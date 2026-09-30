# Copyright 2026 Mozc Date English Project
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests the MSI version boundary without invoking Visual Studio or WiX."""

import json
import os
import pathlib
import tempfile
import types
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from build_tools import product_version
from win32.installer import build_installer


class BuildInstallerTest(unittest.TestCase):

  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.root = pathlib.Path(self.directory.name)
    self.engine_version = self.root / 'mozc_version.txt'
    self.engine_version.write_text(
        'MAJOR=3\nMINOR=34\nBUILD=6239\nREVISION=104\n'
        'TARGET_PLATFORM=Windows\nBUILD_OSS=6239\nQT_VERSION=6\n'
        'ENGINE_VERSION=24\nDATA_VERSION=11\n',
        encoding='utf-8',
    )
    self.product_manifest = self.root / 'product_version.json'
    self.product_manifest.write_text(
        json.dumps(product_version.parse_version('0.2.1').as_manifest()),
        encoding='utf-8',
    )
    self.args = types.SimpleNamespace(
        arch='x64',
        branding='Mozc',
        version_file=str(self.engine_version),
        product_version_file=str(self.product_manifest),
        vs_install_dir='',
        credit_file=str(self.root / 'credits_en.html'),
        qt_core_dll=str(self.root / 'qt/bin/Qt6Core.dll'),
        icon_path=str(self.root / 'product_icon.ico'),
        mozc_tip32=str(self.root / 'mozc_tip32.dll'),
        mozc_tip64=str(self.root / 'mozc_tip64.dll'),
        mozc_tip64arm=None,
        mozc_tip64x=None,
        mozc_broker=str(self.root / 'mozc_broker.exe'),
        mozc_server=str(self.root / 'mozc_server.exe'),
        mozc_cache_service=str(self.root / 'mozc_cache_service.exe'),
        mozc_renderer=str(self.root / 'mozc_renderer.exe'),
        mozc_tool=str(self.root / 'mozc_tool.exe'),
        custom_action=str(self.root / 'custom_action.dll'),
        wix_path=str(self.root / 'wix.exe'),
        wxs_path='installer_oss_64bit.wxs',
        output=str(self.root / 'Mozc64.msi'),
        debug_build=False,
        enable_win_universal_installer=False,
    )
    self.vs_env = mock.patch.object(
        build_installer.vs_util, 'get_vs_env_vars', return_value={
            'VCTOOLSREDISTDIR': str(self.root / 'redist'),
            'VCTOOLSVERSION': '14.44.0',
        }
    ).start()
    self.addCleanup(mock.patch.stopall)
    self.execute = mock.patch.object(build_installer, 'exec_command').start()

  def definitions(self):
    command = self.execute.call_args.args[0]
    return dict(
        command[index + 1].split('=', 1)
        for index, argument in enumerate(command) if argument == '-define'
    )

  def test_mozc_msi_uses_generated_product_version(self):
    with mock.patch.dict(os.environ, {'MOZKEY_PRODUCT_VERSION': '9.9.9'}):
      build_installer.run_wix4(self.args)
    definitions = self.definitions()
    self.assertEqual(definitions['ProductVersion'], '100.2.1')
    self.assertEqual(definitions['MozcVersion'], '3.34.6239.104')
    self.assertEqual(
        definitions['UpgradeCode'], 'DD94B570-B5E2-4100-9D42-61930C611D8A'
    )

  def test_google_branding_keeps_engine_version(self):
    self.args.branding = 'GoogleJapaneseInput'
    self.args.product_version_file = None
    build_installer.run_wix4(self.args)
    definitions = self.definitions()
    self.assertNotIn('ProductVersion', definitions)
    self.assertEqual(definitions['MozcVersion'], '3.34.6239.104')
    self.assertEqual(
        definitions['UpgradeCode'], 'C1A818AF-6EC9-49EF-ADCF-35A40475D156'
    )

  def test_missing_manifest_fails_before_external_tools(self):
    self.args.product_version_file = None
    with self.assertRaisesRegex(ValueError, '--product_version_file'):
      build_installer.run_wix4(self.args)
    self.vs_env.assert_not_called()
    self.execute.assert_not_called()

  def test_mismatched_manifest_fails_before_external_tools(self):
    manifest = product_version.parse_version('0.2.1').as_manifest()
    manifest['msi_version'] = '4.0.0'
    self.product_manifest.write_text(json.dumps(manifest), encoding='utf-8')
    with self.assertRaisesRegex(ValueError, 'inconsistent MSI version'):
      build_installer.run_wix4(self.args)
    self.vs_env.assert_not_called()
    self.execute.assert_not_called()

  def test_upgrade_ranges_use_same_product_version_as_package(self):
    source = pathlib.Path(__file__).with_name('installer_oss_64bit.wxs')
    root = ET.parse(source).getroot()
    namespace = {'wix': 'http://wixtoolset.org/schemas/v4/wxs'}
    package = root.find('wix:Package', namespace)
    self.assertEqual(package.attrib['Version'], '$(var.ProductVersion)')
    ranges = package.findall('wix:Upgrade/wix:UpgradeVersion', namespace)
    self.assertEqual(len(ranges), 2)
    self.assertEqual(ranges[0].attrib['Maximum'], '$(var.ProductVersion)')
    self.assertEqual(ranges[1].attrib['Minimum'], '$(var.ProductVersion)')
    self.assertEqual(ranges[1].attrib['IncludeMinimum'], 'no')


if __name__ == '__main__':
  unittest.main()
