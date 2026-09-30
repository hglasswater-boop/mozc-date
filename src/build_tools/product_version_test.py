# Copyright 2026 Mozc Date English Project
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests the shared product, installer, and release version contract."""

import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from build_tools import product_version


class ProductVersionTest(unittest.TestCase):

  def test_release_version_and_msi_limits(self):
    self.assertEqual(product_version.parse_version('0.2.1').as_manifest(), {
        'product_version': '0.2.1',
        'msi_version': '100.2.1',
        'release_tag': 'v0.2.1',
    })
    self.assertEqual(
        product_version.parse_version('155.255.65535').msi_version,
        '255.255.65535',
    )

  def test_rejects_ambiguous_or_unrepresentable_versions(self):
    values = (
        '', '0.2', '0.2.1.0', 'v0.2.1', '0.2.1-beta', '0.2.1+build',
        '00.2.1', '0.02.1', '0.2.01', '-1.2.1', '+0.2.1', ' 0.2.1',
        '0.2.1\n', '０.2.1', '156.0.0', '0.256.0', '0.0.65536',
        '9' * 5000 + '.0.0',
    )
    for value in values:
      with self.subTest(value=value[:80]), self.assertRaises(ValueError):
        product_version.parse_version(value)

  def test_msi_versions_upgrade_legacy_and_preserve_release_order(self):
    def numeric(value):
      return tuple(map(int, value.split('.')))

    releases = (
        '0.0.0', '0.2.1', '0.2.2', '0.3.0', '1.0.0', '155.255.65535'
    )
    mapped = [
        numeric(product_version.parse_version(v).msi_version) for v in releases
    ]
    self.assertGreater(mapped[0], numeric('3.34.6239'))
    self.assertGreater(mapped[0], numeric('4.0.0'))
    self.assertTrue(all(a < b for a, b in zip(mapped, mapped[1:])))

  def test_override_precedence_and_empty_environment_default(self):
    with tempfile.TemporaryDirectory() as directory:
      source = pathlib.Path(directory) / 'version.txt'
      source.write_text('0.0.0\n', encoding='utf-8')
      self.assertEqual(
          product_version.read_version(source, environ={}).product_version,
          '0.0.0',
      )
      self.assertEqual(
          product_version.read_version(
              source, environ={'MOZKEY_PRODUCT_VERSION': ''}
          ).product_version,
          '0.0.0',
      )
      self.assertEqual(
          product_version.read_version(
              source, environ={'MOZKEY_PRODUCT_VERSION': '0.2.1'}
          ).product_version,
          '0.2.1',
      )
      self.assertEqual(
          product_version.read_version(
              source, '0.2.2', {'MOZKEY_PRODUCT_VERSION': 'bad'}
          ).product_version,
          '0.2.2',
      )
      with self.assertRaises(ValueError):
        product_version.read_version(
            source, environ={'MOZKEY_PRODUCT_VERSION': 'bad'}
        )
      with self.assertRaises(ValueError):
        product_version.read_version(source, '', {})

  def test_cli_outputs_share_one_version(self):
    with tempfile.TemporaryDirectory() as directory:
      source = pathlib.Path(directory) / 'version.txt'
      header = pathlib.Path(directory) / 'product_version_def.h'
      output = pathlib.Path(directory) / 'product_version.json'
      source.write_text('0.0.0\n', encoding='utf-8')
      args = [
          '--version_file', str(source), '--header', str(header),
          '--output', str(output),
      ]
      with mock.patch.dict(os.environ, {'MOZKEY_PRODUCT_VERSION': '0.2.1'}):
        product_version.main(args)
      manifest = json.loads(output.read_text(encoding='utf-8'))
      self.assertEqual(
          product_version.read_manifest(output).product_version, '0.2.1'
      )
      for symbol, key in (
          ('kProductVersion', 'product_version'),
          ('kMsiProductVersion', 'msi_version'),
          ('kProductReleaseTag', 'release_tag'),
      ):
        self.assertIn(
            f'{symbol}[] = "{manifest[key]}";',
            header.read_text(encoding='utf-8'),
        )
      previous_header = header.read_bytes()
      previous_output = output.read_bytes()
      with (
          mock.patch.dict(os.environ, {'MOZKEY_PRODUCT_VERSION': 'bad'}),
          contextlib.redirect_stderr(io.StringIO()),
          self.assertRaises(SystemExit),
      ):
        product_version.main(args)
      self.assertEqual(header.read_bytes(), previous_header)
      self.assertEqual(output.read_bytes(), previous_output)

  def test_manifest_rejects_mismatched_mapping_and_tag(self):
    with tempfile.TemporaryDirectory() as directory:
      output = pathlib.Path(directory) / 'product_version.json'
      valid = product_version.parse_version('0.2.1').as_manifest()
      invalid = (
          dict(valid, msi_version='0.2.1'),
          dict(valid, release_tag='v00.2.1'),
          {'product_version': 1},
          ['0.2.1'],
      )
      for manifest in invalid:
        with self.subTest(manifest=manifest):
          output.write_text(json.dumps(manifest), encoding='utf-8')
          with self.assertRaises(ValueError):
            product_version.read_manifest(output)


if __name__ == '__main__':
  unittest.main()
