# -*- coding: utf-8 -*-
# Copyright 2010-2021, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Generates a bootstrapping Win32 resource script with version info.

  % python gen_win32_resource_header.py --output=out.rc \
      --main=main.rc --version_file=version.txt \
      --product_version_file=product_version.json --branding=Mozc

See mozc_version.py for the detailed information for version.txt.
"""


import logging
import optparse
import os
import pathlib
import sys

from build_tools import mozc_version
from build_tools import product_version


def ParseOptions():
  """Parse command line options.

  Returns:
    An options data.
  """
  parser = optparse.OptionParser()
  parser.add_option('--version_file', dest='version_file')
  parser.add_option('--product_version_file', dest='product_version_file')
  parser.add_option(
      '--branding',
      type='choice',
      choices=['Mozc', 'GoogleJapaneseInput'],
      default='Mozc',
  )
  parser.add_option('--output', dest='output')
  parser.add_option('--main', dest='main')
  parser.add_option('--template', dest='template')
  parser.add_option('--utf8', action='store_true', dest='utf8', default=False)

  (options, unused_args) = parser.parse_args()
  return options


def GenerateBuildProfile():
  """Generate Win32 resource script.

  Returns:
    Build profile string.
  """
  build_details = []

  return '; '.join(build_details)


def GenerateResourceContent(
    version: mozc_version.MozcVersion,
    resource_data: str,
    template_data: str,
    product: product_version.ProductVersion | None = None,
    build_details: str = '',
):
  """Separates Installer file ordering from the displayed product version."""
  if product is None:
    numeric_version = '@MAJOR@,@MINOR@,@BUILD@,@REVISION@'
    display_version = '@MAJOR@.@MINOR@.@BUILD@.@REVISION@'
    file_version = display_version
  else:
    # Windows Installer compares PE FileVersion independently of the package's
    # ProductVersion. Keep both ordered above the historical 3.x/4.x binaries.
    file_version = product.msi_version + '.0'
    numeric_version = file_version.replace('.', ',')
    display_version = product.product_version
  if build_details:
    file_version += f'  ({build_details})'
  bootstrapper_template = (
      f'#define MOZC_RES_VERSION_NUMBER {numeric_version}\n'
      f'#define MOZC_RES_VERSION_STRING "{display_version}"\n'
      f'#define MOZC_RES_SPECIFIC_VERSION_STRING "{file_version}"\n'
      f'{resource_data}\n'
      f'{template_data}\n'
  )
  return version.GetVersionInFormat(bootstrapper_template)


def main():
  """The main function."""
  options = ParseOptions()
  if options.version_file is None:
    logging.error('--version_file is not specified.')
    sys.exit(-1)
  if options.output is None:
    logging.error('--output is not specified.')
    sys.exit(-1)
  if options.main is None:
    logging.error('--main is not specified.')
    sys.exit(-1)
  if options.template is None:
    logging.error('--template is not specified.')
    sys.exit(-1)
  if options.branding == 'Mozc' and options.product_version_file is None:
    logging.error('--product_version_file is required for Mozc branding.')
    sys.exit(-1)

  build_details = GenerateBuildProfile()
  version = mozc_version.MozcVersion(options.version_file)
  product = (
      product_version.read_manifest(pathlib.Path(options.product_version_file))
      if options.branding == 'Mozc' else None
  )

  resource_data = pathlib.Path(options.main).read_text(encoding='utf-8')
  template_data = pathlib.Path(options.template).read_text(encoding='utf-8')

  version_definition = GenerateResourceContent(
      version, resource_data, template_data, product, build_details
  )

  out_encoding = 'utf-8' if options.utf8 else 'utf-16le'
  old_content = ''
  if os.path.exists(options.output):
    # if the target file already exists, need to check the necessity of update.
    try:
      old_content = pathlib.Path(options.output).read_text(encoding=out_encoding)
    except UnicodeError:
      old_content = ''

  if version_definition != old_content:
    pathlib.Path(options.output).write_text(version_definition, encoding=out_encoding)

if __name__ == '__main__':
  main()
