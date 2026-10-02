# Copyright 2026 mozc-date Project
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks ARM64X forwarder resources without requiring an MSVC installation."""

import argparse
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from build_tools import mozc_version
from build_tools import product_version
from win32.tip import build_tip_forwarder_dll


class ForwarderVersionTest(unittest.TestCase):

  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.root = pathlib.Path(self.directory.name)
    self.engine_file = self.root / 'engine.txt'
    self.engine_file.write_text(
        'MAJOR=3\nMINOR=34\nBUILD=6239\nREVISION=102\n'
        'TARGET_PLATFORM=Windows\nBUILD_OSS=6239\nQT_VERSION=6.9.1\n'
        'ENGINE_VERSION=24\nDATA_VERSION=11\n', encoding='utf-8')
    self.engine = mozc_version.MozcVersion(self.engine_file)

  def test_mozc_forwarder_uses_msi_ordering_and_product_display(self):
    info = build_tip_forwarder_dll.ForwarderInfo(
        branding='Mozc', version=self.engine,
        product=product_version.parse_version('0.2.1'))
    output = info.get_rc_file_content()
    self.assertIn('FILEVERSION 100,2,1,0\n', output)
    self.assertIn('PRODUCTVERSION 100,2,1,0\n', output)
    self.assertIn('VALUE "FileVersion", "100.2.1.0"', output)
    self.assertIn('VALUE "ProductVersion", "0.2.1"', output)
    self.assertIn('VALUE "ProductName", "mozc-date"', output)
    self.assertIn('VALUE "OriginalFilename", "mozc_tip64x.dll"', output)
    self.assertNotIn('3.34.6239.102', output)

  def test_google_forwarder_retains_engine_version(self):
    info = build_tip_forwarder_dll.ForwarderInfo(
        branding='GoogleJapaneseInput', version=self.engine,
        product=product_version.parse_version('0.2.1'))
    output = info.get_rc_file_content()
    self.assertIn('FILEVERSION 3,34,6239,102\n', output)
    self.assertIn('PRODUCTVERSION 3,34,6239,102\n', output)
    self.assertIn('VALUE "FileVersion", "3.34.6239.102"', output)
    self.assertIn('VALUE "ProductVersion", "3.34.6239.102"', output)

  def test_mozc_does_not_fall_back_to_engine_version(self):
    info = build_tip_forwarder_dll.ForwarderInfo(branding='Mozc', version=self.engine)
    with self.assertRaisesRegex(ValueError, 'requires a product version manifest'):
      info.get_rc_file_content()

  def test_inconsistent_manifest_fails_before_build_tools_are_invoked(self):
    manifest_file = self.root / 'product.json'
    manifest = product_version.parse_version('0.2.1').as_manifest()
    manifest['msi_version'] = '3.34.6239'
    manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
    args = argparse.Namespace(
        version_file=self.engine_file, branding='Mozc',
        product_version_file=manifest_file)
    with mock.patch.object(build_tip_forwarder_dll.vs_util, 'get_vs_env_vars') as vs_env:
      with self.assertRaises(ValueError):
        build_tip_forwarder_dll.build_on_windows(args)
      vs_env.assert_not_called()


if __name__ == '__main__':
  unittest.main()
