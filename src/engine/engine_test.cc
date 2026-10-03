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

#include "engine/engine.h"

#include <memory>
#include <array>
#include <set>
#include <string>
#include <utility>

#include "absl/log/check.h"
#include "absl/strings/string_view.h"
#include "data_manager/data_manager.h"
#include "data_manager/testing/mock_data_manager.h"
#include "dictionary/dictionary_interface.h"
#include "dictionary/dictionary_token.h"
#include "converter/converter_interface.h"
#include "converter/segments.h"
#include "engine/modules.h"
#include "engine/supplemental_model_interface.h"
#include "protocol/engine_builder.pb.h"
#include "protocol/config.pb.h"
#include "request/conversion_request.h"
#include "testing/gunit.h"
#include "testing/mozctest.h"

namespace mozc {
namespace engine {

namespace {

class SupplementalModelForTesting : public engine::SupplementalModelInterface {
};

constexpr absl::string_view kMockMagicNumber = "MOCK";
constexpr absl::string_view kOssMagicNumber = "\xEFMOZC\x0D\x0A";
constexpr int kMiddlePriority = 50;
}  // namespace

class EngineTest : public ::testing::Test {
 protected:
  EngineTest() {
    const std::string mock_path =
        testing::GetSourcePath({"data_manager", "testing", "mock_mozc.data"});
    mock_request_.set_file_path(mock_path);
    mock_request_.set_magic_number(kMockMagicNumber);
    mock_request_.set_priority(kMiddlePriority);

    const std::string oss_path =
        testing::GetSourcePath({"data_manager", "oss", "mozc.data"});
    oss_request_.set_file_path(oss_path);
    oss_request_.set_magic_number(kOssMagicNumber);
    oss_request_.set_priority(kMiddlePriority);

    const std::string invalid_path =
        testing::GetSourcePath({"data_manager", "invalid", "mozc.data"});
    invalid_path_request_.set_file_path(invalid_path);
    invalid_path_request_.set_magic_number(kOssMagicNumber);
    invalid_path_request_.set_priority(kMiddlePriority);

    invalid_data_request_.set_file_path(mock_path);
    invalid_data_request_.set_magic_number(kOssMagicNumber);
    invalid_data_request_.set_priority(kMiddlePriority);

    mock_version_ = DataManager::CreateFromFile(mock_request_.file_path(),
                                                mock_request_.magic_number())
                        .value()
                        ->GetDataVersion();
    oss_version_ = DataManager::CreateFromFile(oss_request_.file_path(),
                                               oss_request_.magic_number())
                       .value()
                       ->GetDataVersion();
  }

  void SetUp() override {
    engine_ = Engine::CreateEngine();
    engine_->SetAlwaysWaitForTesting(true);
  }

  std::unique_ptr<Engine> engine_;

  std::string mock_version_;
  std::string oss_version_;

  EngineReloadRequest mock_request_;
  EngineReloadRequest oss_request_;
  EngineReloadRequest invalid_path_request_;
  EngineReloadRequest invalid_data_request_;
};

TEST_F(EngineTest, ReloadModulesTest) {
  std::unique_ptr<Modules> modules =
      engine::Modules::Create(std::make_unique<testing::MockDataManager>())
          .value();

  CHECK_OK(engine_->ReloadModules(std::move(modules)));
}

// Use the shipped OSS data and DictionaryImpl, including the standard t13n
// filter. A generator-only test cannot establish that these tokens are shipped.
TEST_F(EngineTest, KatakanaEnglishDictionary) {
  EngineReloadResponse response;
  ASSERT_TRUE(engine_->SendEngineReloadRequest(oss_request_));
  ASSERT_TRUE(engine_->MaybeReloadEngine(&response));
  const auto& lexicon = engine_->GetModulesForTesting().GetDictionary();
  struct Example {
    absl::string_view key;
    absl::string_view english;
  };
  const std::array<Example, 17> examples = {{
      {"こんとろーる", "control"},
      {"こんぴゅーた", "computer"},
      {"こんぴゅーたー", "computer"},
      {"さーば", "server"},
      {"さーばー", "server"},
      {"あいす", "Ice"},
      {"ばす", "bus"},
      {"こあ", "core"},
      {"かー", "car"},
      {"ちゃっとじーぴーてぃー", "ChatGPT"},
      {"じぇみに", "Gemini"},
      {"くろーど", "Claude"},
      {"くろーどこーど", "Claude Code"},
      {"でぃーぷしーく", "DeepSeek"},
      {"ばいぶこーでぃんぐ", "vibe coding"},
      {"えむしーぴー", "MCP"},
      {"えむしーぴ", "MCP"},
  }};
  class Values : public dictionary::DictionaryInterface::Callback {
   public:
    ResultType OnToken(absl::string_view, absl::string_view,
                       dictionary::Token token) override {
      values.insert(token.value);
      return TRAVERSE_CONTINUE;
    }
    std::set<std::string> values;
  };
  for (const auto& example : examples) {
    for (bool enabled : {true, false}) {
      for (bool ascii_completion_enabled : {true, false}) {
        config::Config config;
        config.set_use_t13n_conversion(enabled);
        config.set_use_english_word_dictionary(ascii_completion_enabled);
        const auto request = ConversionRequestBuilder()
                                 .SetConfig(config)
                                 .SetKey(example.key)
                                 .Build();
        Values callback;
        lexicon.LookupExact(example.key, request.options(), &callback);
        EXPECT_EQ(callback.values.count(std::string(example.english)), enabled)
            << example.key << " ascii=" << ascii_completion_enabled;
      }
    }
  }
  // Exercise actual conversion too: English remains a candidate, below the
  // original Japanese loanword. Do not rely only on low-level dictionary lookup.
  for (bool enabled : {true, false}) {
    for (bool ascii_completion_enabled : {true, false}) {
      config::Config config;
      config.set_use_t13n_conversion(enabled);
      config.set_use_english_word_dictionary(ascii_completion_enabled);
      const auto request = ConversionRequestBuilder()
                               .SetConfig(config)
                               .SetKey("こんとろーる")
                               .Build();
      Segments segments;
      ASSERT_TRUE(engine_->GetConverter()->StartConversion(request, &segments));
      ASSERT_EQ(segments.conversion_segments_size(), 1);
      const auto& segment = segments.conversion_segment(0);
      ASSERT_GT(segment.candidates_size(), 0);
      EXPECT_EQ(segment.candidate(0).value, "コントロール");
      bool found = false;
      for (size_t i = 0; i < segment.candidates_size(); ++i) {
        found |= segment.candidate(i).value == "control";
      }
      EXPECT_EQ(found, enabled);
    }
  }
  // Confirm each reviewed supplement entry can be selected by the actual
  // converter, including compounds and the terminal-long-vowel alias.
  const std::array<Example, 6> modern_examples = {{
      {"くろーど", "Claude"},
      {"くろーどこーど", "Claude Code"},
      {"でぃーぷしーく", "DeepSeek"},
      {"ばいぶこーでぃんぐ", "vibe coding"},
      {"えむしーぴー", "MCP"},
      {"えむしーぴ", "MCP"},
  }};
  for (const auto& example : modern_examples) {
    for (bool enabled : {true, false}) {
      for (bool ascii_completion_enabled : {true, false}) {
        config::Config config;
        config.set_use_t13n_conversion(enabled);
        config.set_use_english_word_dictionary(ascii_completion_enabled);
        const auto request = ConversionRequestBuilder()
                                 .SetConfig(config)
                                 .SetKey(example.key)
                                 .Build();
        Segments segments;
        ASSERT_TRUE(engine_->GetConverter()->StartConversion(request, &segments))
            << example.key;
        bool found = false;
        for (int segment_index = 0;
             segment_index < segments.conversion_segments_size();
             ++segment_index) {
          const auto& segment = segments.conversion_segment(segment_index);
          for (int candidate_index = 0;
               candidate_index < segment.candidates_size(); ++candidate_index) {
            found |= segment.candidate(candidate_index).value == example.english;
          }
        }
        EXPECT_EQ(found, enabled)
            << example.key << " ascii=" << ascii_completion_enabled;
      }
    }
  }
}

// Tests the interaction with DataLoader for successful Engine
// reload event.
TEST_F(EngineTest, DataLoadSuccessfulScenarioTest) {
  EngineReloadResponse response;

  // The engine is not updated yet.
  EXPECT_NE(engine_->GetDataVersion(), mock_version_);

  // The engine is updated with the request.
  EXPECT_TRUE(engine_->SendEngineReloadRequest(mock_request_));
  EXPECT_TRUE(engine_->MaybeReloadEngine(&response));
  EXPECT_EQ(engine_->GetDataVersion(), mock_version_);

  // The engine is not updated with the same request.
  EXPECT_FALSE(engine_->SendEngineReloadRequest(mock_request_));
  EXPECT_FALSE(engine_->MaybeReloadEngine(&response));
  EXPECT_EQ(engine_->GetDataVersion(), mock_version_);
}

// Tests situations to handle multiple new requests.
TEST_F(EngineTest, DataUpdateSuccessfulScenarioTest) {
  EngineReloadResponse response;

  // Send a request, and update the engine.
  EXPECT_TRUE(engine_->SendEngineReloadRequest(mock_request_));
  EXPECT_TRUE(engine_->MaybeReloadEngine(&response));
  EXPECT_EQ(engine_->GetDataVersion(), mock_version_);

  // Send another request, and update the engine again.
  EXPECT_TRUE(engine_->SendEngineReloadRequest(oss_request_));
  EXPECT_TRUE(engine_->MaybeReloadEngine(&response));
  EXPECT_EQ(engine_->GetDataVersion(), oss_version_);
}

// Tests the interaction with DataLoader in the situation where
// requested data is broken.
TEST_F(EngineTest, ReloadInvalidDataTest) {
  EXPECT_TRUE(engine_->SendEngineReloadRequest(invalid_path_request_));

  // The new request is performed, but it returns invalid data.
  EngineReloadResponse response;
  EXPECT_FALSE(engine_->MaybeReloadEngine(&response));

  // Sends the same request again, but the request is already marked as
  // unregistered.
  EXPECT_FALSE(engine_->SendEngineReloadRequest(invalid_path_request_));
  EXPECT_FALSE(engine_->MaybeReloadEngine(&response));
}

// Tests the rollback scenario
TEST_F(EngineTest, RollbackDataTest) {
  // Sends multiple requests three times.
  EXPECT_TRUE(engine_->SendEngineReloadRequest(mock_request_));
  EXPECT_TRUE(engine_->SendEngineReloadRequest(invalid_path_request_));
  EXPECT_TRUE(engine_->SendEngineReloadRequest(invalid_data_request_));

  // The last two requests are invalid. The first request is immediately used as
  // a fallback.
  EngineReloadResponse response;
  EXPECT_TRUE(engine_->MaybeReloadEngine(&response));
  EXPECT_EQ(response.request().file_path(), mock_request_.file_path());

  // DataVersion comes from the first request (i.e. mock_request_).
  EXPECT_EQ(engine_->GetDataVersion(), mock_version_);
}
}  // namespace engine
}  // namespace mozc
