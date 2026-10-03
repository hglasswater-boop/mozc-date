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

#include "rewriter/english_word_dictionary_rewriter.h"

#include <cstddef>
#include <string>
#include <vector>

#include "absl/strings/string_view.h"
#include "config/config_handler.h"
#include "converter/attribute.h"
#include "converter/candidate.h"
#include "converter/segments.h"
#include "protocol/config.pb.h"
#include "request/conversion_request.h"
#include "rewriter/rewriter_interface.h"
#include "testing/gunit.h"

namespace mozc {
namespace {

Segment* AddInputSegment(absl::string_view key, Segments* segments) {
  Segment* segment = segments->push_back_segment();
  segment->set_key(key);
  converter::Candidate* raw = segment->add_candidate();
  raw->key = std::string(key);
  raw->content_key = raw->key;
  raw->value = std::string(key);
  raw->content_value = raw->value;
  return segment;
}

const converter::Candidate* FindCandidate(const Segment& segment,
                                          absl::string_view value) {
  for (const converter::Candidate* candidate : segment.candidates()) {
    if (candidate != nullptr && candidate->value == value) {
      return candidate;
    }
  }
  return nullptr;
}

ConversionRequest BuildRequest(absl::string_view key, RequestType type,
                               bool dictionary_enabled = true,
                               bool spelling_enabled = true) {
  config::Config config;
  config::ConfigHandler::GetDefaultConfig(&config);
  config.set_use_english_word_dictionary(dictionary_enabled);
  config.set_use_english_spelling_correction(spelling_enabled);
  return ConversionRequestBuilder()
      .SetConfig(config)
      .SetRequestType(type)
      .SetKey(key)
      .Build();
}

void InsertASCIISequence(absl::string_view text, composer::Composer* composer) {
  for (const char c : text) {
    commands::KeyEvent key;
    key.set_key_code(c);
    composer->InsertCharacterKeyEvent(key);
  }
}

bool HasPossessiveSuffix(absl::string_view value) {
  return value.size() >= 2 && value.substr(value.size() - 2) == "'s";
}

}  // namespace

TEST(EnglishWordDictionaryRewriterTest, CompletesCanonicalTechWord) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("gith", &segments);

  const ConversionRequest request = BuildRequest("gith", RequestType::SUGGESTION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));

  const converter::Candidate* candidate = FindCandidate(*segment, "GitHub");
  ASSERT_NE(candidate, nullptr);
  EXPECT_EQ(candidate->description, "英単語補完");
  EXPECT_FALSE(candidate->attributes & converter::Attribute::SPELLING_CORRECTION);
}

TEST(EnglishWordDictionaryRewriterTest, CompletesGeneralEnglishWord) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("prope", &segments);

  const ConversionRequest request = BuildRequest("prope", RequestType::SUGGESTION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "property"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, RanksEntirePrefixRange) {
  EnglishWordDictionaryRewriter rewriter;
  struct TestCase {
    absl::string_view prefix;
    absl::string_view expected;
  };
  constexpr TestCase kCases[] = {
      {"pre", "press"},
      {"dis", "dish"},
      {"sta", "stay"},
  };

  for (const TestCase& test_case : kCases) {
    SCOPED_TRACE(test_case.prefix);
    Segments segments;
    Segment* segment = AddInputSegment(test_case.prefix, &segments);
    const ConversionRequest request =
        BuildRequest(test_case.prefix, RequestType::SUGGESTION);
    EXPECT_TRUE(rewriter.Rewrite(request, &segments));
    EXPECT_NE(FindCandidate(*segment, test_case.expected), nullptr);
  }
}

TEST(EnglishWordDictionaryRewriterTest,
     DoesNotSuggestPossessiveWithoutApostrophe) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("co", &segments);

  const ConversionRequest request = BuildRequest("co", RequestType::SUGGESTION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  for (const converter::Candidate* candidate : segment->candidates()) {
    ASSERT_NE(candidate, nullptr);
    EXPECT_FALSE(HasPossessiveSuffix(candidate->value)) << candidate->value;
  }
}

TEST(EnglishWordDictionaryRewriterTest, CompletesWordForExplicitPrediction) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("gith", &segments);

  const ConversionRequest request = BuildRequest("gith", RequestType::PREDICTION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "GitHub"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, UsesComposerRawInputForRomajiTyping) {
  EnglishWordDictionaryRewriter rewriter;
  composer::Composer composer;
  InsertASCIISequence("gith", &composer);

  const std::string composition = composer.GetStringForPreedit();
  EXPECT_NE(composition, "gith");

  Segments segments;
  Segment* segment = AddInputSegment(composition, &segments);

  config::Config config;
  config::ConfigHandler::GetDefaultConfig(&config);
  config.set_use_english_word_dictionary(true);
  config.set_use_english_spelling_correction(true);
  const ConversionRequest request =
      ConversionRequestBuilder()
          .SetComposer(composer)
          .SetConfig(config)
          .SetRequestType(RequestType::SUGGESTION)
          .Build();

  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "GitHub"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, KeepsCompletionsWhenOpeningPrediction) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("And", &segments);
  ASSERT_TRUE(rewriter.Rewrite(BuildRequest("And", RequestType::SUGGESTION),
                               &segments));
  ASSERT_EQ(segment->candidate(1).value, "Android");
  std::vector<std::string> suggestions;
  for (const converter::Candidate* candidate : segment->candidates()) {
    suggestions.push_back(candidate->value);
  }

  const ConversionRequest prediction = BuildRequest("And", RequestType::PREDICTION);
  EXPECT_FALSE(rewriter.Rewrite(prediction, &segments));
  ASSERT_EQ(segment->candidates_size(), suggestions.size());
  for (size_t i = 0; i < suggestions.size(); ++i) {
    EXPECT_EQ(segment->candidate(i).value, suggestions[i]);
  }
  // A second Tab must not grow the list or change the same candidate order.
  EXPECT_FALSE(rewriter.Rewrite(prediction, &segments));
  EXPECT_EQ(segment->candidates_size(), suggestions.size());
}

TEST(EnglishWordDictionaryRewriterTest, KeepsTruncatedRomajiSuggestionsOnFirstPage) {
  EnglishWordDictionaryRewriter rewriter;
  composer::Composer composer;
  InsertASCIISequence("And", &composer);
  Segments segments;
  Segment* segment = AddInputSegment(composer.GetStringForPreedit(), &segments);
  for (const absl::string_view value : {"Android", "Androids"}) {
    converter::Candidate* candidate = segment->add_candidate();
    candidate->value = std::string(value);
    candidate->description = "英単語補完";
    candidate->attributes = converter::Attribute::NO_VARIANTS_EXPANSION;
  }
  config::Config config;
  config::ConfigHandler::GetDefaultConfig(&config);
  config.set_use_english_word_dictionary(true);
  const ConversionRequest prediction = ConversionRequestBuilder()
      .SetComposer(composer)
      .SetConfig(config)
      .SetRequestType(RequestType::PREDICTION)
      .Build();

  ASSERT_TRUE(rewriter.Rewrite(prediction, &segments));
  EXPECT_EQ(segment->candidate(0).value, composer.GetStringForPreedit());
  EXPECT_EQ(segment->candidate(1).value, "Android");
  EXPECT_EQ(segment->candidate(2).value, "Androids");
  EXPECT_EQ(segment->candidate(1).description, "英単語補完");
  EXPECT_LE(segment->candidates_size(), 9);
  EXPECT_FALSE(rewriter.Rewrite(prediction, &segments));
}

TEST(EnglishWordDictionaryRewriterTest, PreservesTopCandidateWhenAlreadyCompletion) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("Android", &segments);
  segment->set_key("And");
  ASSERT_TRUE(rewriter.Rewrite(BuildRequest("And", RequestType::PREDICTION),
                               &segments));
  EXPECT_EQ(segment->candidate(0).value, "Android");
  EXPECT_EQ(segment->candidate(1).value, "Androids");
  EXPECT_LE(segment->candidates_size(), 9);
  EXPECT_FALSE(rewriter.Rewrite(BuildRequest("And", RequestType::PREDICTION),
                                &segments));
}

TEST(EnglishWordDictionaryRewriterTest, CorrectsTransposedSpelling) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("recieve", &segments);

  const ConversionRequest request = BuildRequest("recieve", RequestType::CONVERSION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));

  const converter::Candidate* candidate = FindCandidate(*segment, "receive");
  ASSERT_NE(candidate, nullptr);
  EXPECT_EQ(candidate->description, "英語スペル候補");
  EXPECT_TRUE(candidate->attributes & converter::Attribute::SPELLING_CORRECTION);
  EXPECT_EQ(candidate->prefix, "→ ");
}

TEST(EnglishWordDictionaryRewriterTest, CorrectsSubstitutionSpelling) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("proparty", &segments);

  const ConversionRequest request = BuildRequest("proparty", RequestType::CONVERSION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "property"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest,
     SpellingCorrectionWorksWhenCompletionIsDisabled) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("recieve", &segments);

  const ConversionRequest request =
      BuildRequest("recieve", RequestType::CONVERSION, false, true);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "receive"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest,
     CompletionDoesNotRunWhenCompletionIsDisabled) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("gith", &segments);

  const ConversionRequest request =
      BuildRequest("gith", RequestType::SUGGESTION, false, true);
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  EXPECT_EQ(FindCandidate(*segment, "GitHub"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest,
     SpellingDoesNotRunWhenSpellingIsDisabled) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("recieve", &segments);

  const ConversionRequest request =
      BuildRequest("recieve", RequestType::CONVERSION, true, false);
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  EXPECT_EQ(FindCandidate(*segment, "receive"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, BothSwitchesDisabled) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("gith", &segments);

  const ConversionRequest request =
      BuildRequest("gith", RequestType::SUGGESTION, false, false);
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  EXPECT_EQ(FindCandidate(*segment, "GitHub"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, DoesNotRunSpellingScanForSuggestion) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("recieve", &segments);

  const ConversionRequest request = BuildRequest("recieve", RequestType::SUGGESTION);
  rewriter.Rewrite(request, &segments);
  EXPECT_EQ(FindCandidate(*segment, "receive"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, DoesNotInjectCompletionIntoConversion) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("gith", &segments);

  const ConversionRequest request =
      BuildRequest("gith", RequestType::CONVERSION, true, false);
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  EXPECT_EQ(FindCandidate(*segment, "GitHub"), nullptr);
}

TEST(EnglishWordDictionaryRewriterTest, CapabilityTracksEnabledFeatures) {
  EnglishWordDictionaryRewriter rewriter;

  const ConversionRequest prediction_only =
      BuildRequest("gith", RequestType::SUGGESTION, true, false);
  EXPECT_EQ(rewriter.capability(prediction_only),
            RewriterInterface::PREDICTION | RewriterInterface::SUGGESTION);

  const ConversionRequest spelling_only =
      BuildRequest("gith", RequestType::SUGGESTION, false, true);
  EXPECT_EQ(rewriter.capability(spelling_only), RewriterInterface::CONVERSION);

  const ConversionRequest all =
      BuildRequest("gith", RequestType::SUGGESTION, true, true);
  EXPECT_EQ(rewriter.capability(all), RewriterInterface::ALL);

  const ConversionRequest none =
      BuildRequest("gith", RequestType::SUGGESTION, false, false);
  EXPECT_EQ(rewriter.capability(none), RewriterInterface::NOT_AVAILABLE);
}

TEST(EnglishWordDictionaryRewriterTest, PreservesUppercaseInputIntent) {
  EnglishWordDictionaryRewriter rewriter;
  Segments segments;
  Segment* segment = AddInputSegment("GITH", &segments);

  const ConversionRequest request = BuildRequest("GITH", RequestType::SUGGESTION);
  EXPECT_TRUE(rewriter.Rewrite(request, &segments));
  EXPECT_NE(FindCandidate(*segment, "GITHUB"), nullptr);
}

}  // namespace mozc
