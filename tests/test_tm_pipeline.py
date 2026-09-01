"""Unit tests for the isolated Turkmen conversational profile."""

import asyncio
import json
import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot
import tm_translation as tm


class FakeResponses:
    def __init__(self, *values):
        self.values = iter(values)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=next(self.values))


class TurkmenPipelineTests(unittest.TestCase):
    def test_assets_and_regression_set_are_present(self):
        root = Path(__file__).resolve().parents[1]
        examples = json.loads((root / "data" / "tm_translation_examples.json").read_text(encoding="utf-8"))
        cases = json.loads((root / "tests" / "tm_translation_cases.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(examples), 100)
        self.assertGreaterEqual(len(cases), 200)
        self.assertTrue((root / "data" / "tm_style_profile.json").exists())
        self.assertTrue((root / "data" / "tm_spelling_variants.json").exists())

    def test_deployed_references_are_anonymous_and_metadata_free(self):
        root = Path(__file__).resolve().parents[1]
        rows = json.loads((root / "data" / "tm_style_references.json").read_text(encoding="utf-8"))
        private_pattern = re.compile(r"https?://|t\.me/|@[A-Za-z0-9_]{4,}|\+?\d[\d ()-]{7,}\d", re.I)
        self.assertEqual(600, len(rows))
        for row in rows:
            self.assertFalse(private_pattern.search(row["text"]))
            self.assertFalse({"name", "from", "from_id", "user_id"} & set(row))

    def test_direction_and_language_detection(self):
        self.assertEqual("ru_to_tm", tm.choose_direction("скинь скрин"))
        self.assertEqual("tm_to_ru", tm.choose_direction("skrin ugrat brat"))
        self.assertEqual("tm_to_ru", tm.choose_direction("men hazir bararyn да брат"))
        self.assertTrue(tm.looks_turkmen("Men oyuncym utan yagdaynda"))
        self.assertTrue(tm.is_turkmen_language("Türkmençe (туркменский)"))

    def test_context_is_capped_and_other_languages_are_filtered(self):
        history = [{"direction": "incoming", "text": "old English context"}]
        history += [{"direction": "incoming", "text": f"pul {index} geldi"} for index in range(8)]
        built = tm.build_input("a ertir", history)
        self.assertNotIn("old English context", built)
        self.assertNotIn("pul 2 geldi", built)
        self.assertIn("pul 3 geldi", built)
        self.assertIn("Translate ONLY this message:\na ertir", built)

    def test_ascii_output_removes_marks_but_keeps_source_punctuation_and_entities(self):
        source = "Salam, nähili ýagdaýlaryň? 8%, 2% @manager https://t.me/example"
        expected = "Salam, nahili yagdaylaryn? 8%, 2% @manager https://t.me/example"
        with patch.dict(os.environ, {"TM_OUTPUT_STYLE": "tm_ascii_chat"}):
            self.assertEqual(expected, tm.normalize_output(source, "casual"))

    def test_percentage_is_a_protected_entity(self):
        self.assertIn("percentages", tm.missing_or_changed_entities("комиссия 8%", "komissiya 8"))
        self.assertEqual([], tm.missing_or_changed_entities("8% и 2%", "8% we 2%"))

    def test_prompt_uses_real_style_references_as_style_only(self):
        instructions = tm.build_instructions("скинь скрин", "ru_to_tm", "casual")
        self.assertIn("TARGET LANGUAGE STYLE REFERENCES", instructions)
        self.assertIn("Do not copy their meaning", instructions)
        self.assertIn("Accuracy is more important", instructions)
        self.assertIn("basic ASCII Latin", instructions)

    def test_retry_and_normalization_are_applied(self):
        fake = FakeResponses("Salam, brat, nähili ýagdaýlaryň?")
        previous = bot.client
        bot.client = SimpleNamespace(responses=fake)
        try:
            with patch.dict(os.environ, {"TM_OUTPUT_STYLE": "tm_ascii_chat"}):
                result = asyncio.run(bot.translate_turkmen_conversational("привет брат как дела", "ru_to_tm"))
        finally:
            bot.client = previous
        self.assertEqual("Salam, brat, nahili yagdaylaryn?", result)
        self.assertEqual(1, len(fake.calls))

    def test_changed_number_causes_retry(self):
        fake = FakeResponses("350 TMT ugrat", "250 TMT ugrat")
        previous = bot.client
        bot.client = SimpleNamespace(responses=fake)
        try:
            result = asyncio.run(bot.translate_turkmen_conversational("скинь 250 TMT", "ru_to_tm"))
        finally:
            bot.client = previous
        self.assertEqual("250 TMT ugrat", result)
        self.assertEqual(2, len(fake.calls))

    def test_feature_flag_routes_only_turkmen_target(self):
        previous_flag = bot.TURKMEN_CONVERSATIONAL_MODE
        previous_translator = bot.translate_turkmen_conversational
        mocked = AsyncMock(return_value="salam")
        bot.TURKMEN_CONVERSATIONAL_MODE = True
        bot.translate_turkmen_conversational = mocked
        try:
            result = asyncio.run(bot.translate_text("привет", "Türkmençe (туркменский)"))
        finally:
            bot.TURKMEN_CONVERSATIONAL_MODE = previous_flag
            bot.translate_turkmen_conversational = previous_translator
        self.assertEqual("salam", result)
        mocked.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
