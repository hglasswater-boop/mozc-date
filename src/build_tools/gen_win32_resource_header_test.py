# Copyright 2026 Mozc Date English Project
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks the version fields consumed by Windows Installer and Explorer."""

import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

from build_tools import gen_win32_resource_header
from build_tools import product_version


class Win32ResourceVersionTest(unittest.TestCase):

  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.root = pathlib.Path(self.directory.name)
    self.engine = self.root / 'engine.txt'
    self.engine.write_text(
        'MAJOR=3\nMINOR=34\nBUILD=6239\nREVISION=102\n'
        'TARGET_PLATFORM=Windows\nBUILD_OSS=6239\nQT_VERSION=6.9.1\n'
        'ENGINE_VERSION=24\nDATA_VERSION=11\n', encoding='utf-8')
    self.manifest = self.root / 'product.json'
    self.manifest.write_text(
        json.dumps(product_version.parse_version('0.2.1').as_manifest()),
        encoding='utf-8')
    self.main = self.root / 'main.rc'
    self.main.write_text('#include "winres.h"\n', encoding='utf-8')
    self.output = self.root / 'generated.rc'
    self.template = pathlib.Path(gen_win32_resource_header.__file__).with_name(
        'mozc_win32_resource_template.rc')

  def generate(self, branding='Mozc', utf8=True, manifest=True):
    args = [
        'gen_win32_resource_header', '--version_file', str(self.engine),
        '--main', str(self.main), '--template', str(self.template),
        '--output', str(self.output), '--branding', branding,
    ]
    if utf8:
      args.append('--utf8')
    if manifest:
      args.extend(['--product_version_file', str(self.manifest)])
    with mock.patch.object(sys, 'argv', args):
      gen_win32_resource_header.main()
    return self.output.read_text(encoding='utf-8' if utf8 else 'utf-16le')

  def test_mozc_numeric_versions_upgrade_legacy_files_and_display_product(self):
    output = self.generate()
    self.assertIn('#define MOZC_RES_VERSION_NUMBER 100,2,1,0\n', output)
    self.assertIn('#define MOZC_RES_VERSION_STRING "0.2.1"\n', output)
    self.assertIn('#define MOZC_RES_SPECIFIC_VERSION_STRING "100.2.1.0"\n', output)
    self.assertIn('#define MOZC_RES_FILE_VERSION_NUMBER MOZC_RES_VERSION_NUMBER', output)
    self.assertIn('#define MOZC_RES_PRODUCT_VERSION_NUMBER MOZC_RES_VERSION_NUMBER', output)
    self.assertIn('FILEVERSION MOZC_RES_FILE_VERSION_NUMBER', output)
    self.assertIn('PRODUCTVERSION MOZC_RES_PRODUCT_VERSION_NUMBER', output)
    self.assertNotIn('3.34.6239.102', output)
    numeric_version = tuple(map(int, re.search(
        r'^#define MOZC_RES_VERSION_NUMBER ([0-9,]+)$', output,
        re.MULTILINE).group(1).split(',')))
    self.assertGreater(numeric_version, (4, 0, 0, 0))
    self.assertGreater(numeric_version, (3, 34, 6239, 104))

  def test_default_output_is_windows_utf16_resource_script(self):
    self.assertIn('#define MOZC_RES_VERSION_NUMBER 100,2,1,0\n', self.generate(utf8=False))

  def test_google_branding_keeps_engine_version_and_ignores_product_manifest(self):
    self.manifest.write_text('invalid JSON', encoding='utf-8')
    output = self.generate(branding='GoogleJapaneseInput')
    self.assertIn('#define MOZC_RES_VERSION_NUMBER 3,34,6239,102\n', output)
    self.assertIn('#define MOZC_RES_VERSION_STRING "3.34.6239.102"\n', output)
    self.assertIn('#define MOZC_RES_SPECIFIC_VERSION_STRING "3.34.6239.102"\n', output)

  def test_mozc_rejects_missing_or_inconsistent_manifest_before_output(self):
    self.output.write_text('previous output', encoding='utf-8')
    with self.assertLogs(level='ERROR'), self.assertRaises(SystemExit):
      self.generate(manifest=False)
    self.assertEqual(self.output.read_text(encoding='utf-8'), 'previous output')
    manifest = product_version.parse_version('0.2.1').as_manifest()
    manifest['msi_version'] = '3.34.6239'
    self.manifest.write_text(json.dumps(manifest), encoding='utf-8')
    with self.assertRaises(ValueError):
      self.generate()
    self.assertEqual(self.output.read_text(encoding='utf-8'), 'previous output')


if __name__ == '__main__':
  unittest.main()
