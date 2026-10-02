// Copyright 2010-2021, Google Inc.
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//     * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//     * Neither the name of Google Inc. nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include "base/version.h"

#include <algorithm>
#include <string>
#include <vector>

#include "absl/strings/str_format.h"
#include "absl/strings/str_split.h"
#include "base/number_util.h"
#include "testing/gunit.h"

// Import the generated version_def.h.
#include "base/product_version_def.h"
#include "base/version_def.h"

namespace mozc {

TEST(VersionTest, BasicTest) {
  EXPECT_EQ(Version::GetMozcVersion(), version::kMozcVersion);
}

TEST(VersionTest, ProductVersion) {
  const std::string product = Version::GetProductVersion();
  const std::string msi = Version::GetMsiProductVersion();
  EXPECT_EQ(product, version::kProductVersion);
  EXPECT_EQ(msi, version::kMsiProductVersion);
  const std::vector<std::string> product_fields = absl::StrSplit(product, '.');
  const std::vector<std::string> msi_fields = absl::StrSplit(msi, '.');
  ASSERT_TRUE(product_fields.size() == 3 || product_fields.size() == 4);
  if (product_fields.size() == 4) {
    EXPECT_EQ(product_fields[3], "0");
  }
  ASSERT_EQ(msi_fields.size(), 3);
  EXPECT_EQ(NumberUtil::SimpleAtoi(msi_fields[0]),
            100 + NumberUtil::SimpleAtoi(product_fields[0]));
  EXPECT_EQ(msi_fields[1], product_fields[1]);
  EXPECT_EQ(msi_fields[2], product_fields[2]);
  const std::string engine = Version::GetMozcVersion();
  EXPECT_EQ(std::count(engine.begin(), engine.end(), '.'), 3);
}

TEST(VersionTest, VersionNumberTest) {
  const int major = Version::GetMozcVersionMajor();
  const int minor = Version::GetMozcVersionMinor();
  const int build_number = Version::GetMozcVersionBuildNumber();
  const int revision = Version::GetMozcVersionRevision();
  EXPECT_EQ(
      Version::GetMozcVersion(),
      absl::StrFormat("%d.%d.%d.%d", major, minor, build_number, revision));
}

TEST(VersionTest, CompareVersion) {
  EXPECT_FALSE(Version::CompareVersion("0.0.0.0", "0.0.0.0"));
  EXPECT_FALSE(Version::CompareVersion("1.2.3.4", "1.2.3.4"));
  EXPECT_TRUE(Version::CompareVersion("0.0.0.0", "0.0.0.1"));
  EXPECT_TRUE(Version::CompareVersion("0.0.1.2", "0.1.2.3"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "5.2.3.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.5.3.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.2.5.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.2.3.5"));
  EXPECT_FALSE(Version::CompareVersion("5.2.3.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.5.3.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.2.5.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.2.3.5", "1.2.3.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "15.2.3.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.25.3.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.2.35.4"));
  EXPECT_TRUE(Version::CompareVersion("1.2.3.4", "1.2.3.45"));
  EXPECT_FALSE(Version::CompareVersion("15.2.3.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.25.3.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.2.35.4", "1.2.3.4"));
  EXPECT_FALSE(Version::CompareVersion("1.2.3.45", "1.2.3.4"));

  // Always return false if "Unknown" is passed.
  EXPECT_FALSE(Version::CompareVersion("Unknown", "Unknown"));
  EXPECT_FALSE(Version::CompareVersion("0.0.0.0", "(Unknown)"));
  EXPECT_FALSE(Version::CompareVersion("Unknown", "0.0.0.0"));
  EXPECT_FALSE(Version::CompareVersion("0.0.0.0", "Unknown"));
  EXPECT_FALSE(Version::CompareVersion("(Unknown)", "(Unknown)"));
  EXPECT_FALSE(Version::CompareVersion("(Unknown)", "0.0.0.0"));
}

}  // namespace mozc
