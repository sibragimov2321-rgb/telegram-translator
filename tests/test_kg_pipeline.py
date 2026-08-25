import asyncio
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import bot
import kg_translation as kg


ROOT = Path(__file__).resolve().parents[1]


class FakeResponses:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=next(self.outputs))


class KyrgyzAssetTests(unittest.TestCase):
    def test_curated_examples_cover_both_directions(self):
        rows = json.loads((ROOT / "data" / "kg_translation_examples.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(rows), 100)
        self.assertTrue(any(row["target_language"] == "ky" for row in rows))
        self.assertTrue(any(row["target_language"] == "ru" for row in rows))

    def test_regression_set_has_required_size_and_categories(self):
        rows = json.loads((ROOT / "tests" / "kg_translation_cases.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(rows), 150)
        categories = {row["category"] for row in rows}
        required = {
            "one_word", "very_short", "casual", "slang", "money", "transfers", "numbers",
            "questions", "requests", "screenshots", "Telegram", "mixed_ru_ky", "no_punctuation",
            "typos", "emoji", "formal", "negative_statements",
        }
        self.assertFalse(required - categories)
        self.assertTrue(any(row["direction"] == "ru_to_ky" for row in rows))
        self.assertTrue(any(row["direction"] == "ky_to_ru" for row in rows))

    def test_corpus_is_anonymous_and_compact(self):
        corpus_path = ROOT / "data" / "kg_conversational_corpus.jsonl"
        if not corpus_path.exists():
            self.skipTest("private offline corpus is intentionally not committed")
        self.assertLess(corpus_path.stat().st_size, 8 * 1024 * 1024)
        pii = re.compile(r"https?://|t\.me/|@[A-Za-z0-9_]{4,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\d{7,}")
        count = 0
        with corpus_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                self.assertEqual({"text", "language", "style"}, set(row))
                self.assertNotRegex(row["text"], pii)
                count += 1
        self.assertGreaterEqual(count, 10_000)

    def test_deployed_style_references_are_anonymous(self):
        references = (ROOT / "data" / "kg_style_references.json").read_text(encoding="utf-8")
        pii = re.compile(r"https?://|t\.me/|@[A-Za-z0-9_]{4,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\d{7,}")
        self.assertNotRegex(references, pii)


class KyrgyzPromptTests(unittest.TestCase):
    def test_style_retrieval_is_bounded_and_marked_as_non_translation(self):
        references = kg.retrieve_style_references("скинь скрин", "very_casual")
        self.assertGreaterEqual(len(references), 5)
        self.assertLessEqual(len(references), kg.STYLE_REFERENCE_LIMIT)
        instructions = kg.build_instructions("скинь скрин", "ru_to_ky", "very_casual")
        self.assertIn("These are NOT translations", instructions)
        self.assertIn("Accuracy is always more important", instructions)
        self.assertNotIn("result1.json", instructions)

    def test_context_uses_only_last_five_messages(self):
        history = [{"direction": "incoming", "text": f"message {index}"} for index in range(8)]
        model_input = kg.build_input("а завтра", history)
        self.assertNotIn("message 2", model_input)
        self.assertIn("message 3", model_input)
        self.assertIn("message 7", model_input)
        self.assertIn("Translate ONLY this message:\nа завтра", model_input)

    def test_mixed_language_and_kyrgyz_direction_heuristics(self):
        self.assertEqual("ru_to_ky", kg.choose_direction("брат азыр 500 сом скинешь"))
        self.assertEqual("ky_to_ru", kg.choose_direction("менде доступ жок"))
        self.assertTrue(kg.looks_kyrgyz("акча качан түшөт"))
        self.assertFalse(kg.looks_kyrgyz("когда придут деньги"))

    def test_entity_validation_preserves_values(self):
        source = "скинь 3500 сом на @manager до 21.08"
        good = "3500 сомду @manager ге 21.08 чейин жибер"
        bad = "3000 сомду башка адамга жибер"
        self.assertEqual([], kg.missing_or_changed_entities(source, good))
        self.assertIn("numbers", kg.missing_or_changed_entities(source, bad))
        self.assertIn("usernames", kg.missing_or_changed_entities(source, bad))

    def test_short_message_expansion_is_rejected(self):
        problems = kg.translation_needs_retry("канча", "Скажите пожалуйста какую именно сумму вы имеете в виду", "ky_to_ru")
        self.assertIn("short_message_expanded", problems)


class KyrgyzBotRoutingTests(unittest.TestCase):
    def test_new_mode_routes_only_kyrgyz_target(self):
        previous_client = bot.client
        previous_flag = bot.KYRGYZ_CONVERSATIONAL_MODE
        fake = FakeResponses("500 сом жибер")
        bot.client = SimpleNamespace(responses=fake)
        bot.KYRGYZ_CONVERSATIONAL_MODE = True
        try:
            result = asyncio.run(bot.translate_text("скинь 500 сом", "Kyrgyz"))
        finally:
            bot.client = previous_client
            bot.KYRGYZ_CONVERSATIONAL_MODE = previous_flag
        self.assertEqual("500 сом жибер", result)
        self.assertEqual(0.2, fake.calls[0]["temperature"])
        self.assertIn("conversational Kyrgyz", fake.calls[0]["instructions"])

    def test_other_language_stays_on_legacy_pipeline(self):
        previous_client = bot.client
        previous_flag = bot.KYRGYZ_CONVERSATIONAL_MODE
        fake = FakeResponses("hello")
        bot.client = SimpleNamespace(responses=fake)
        bot.KYRGYZ_CONVERSATIONAL_MODE = True
        try:
            result = asyncio.run(bot.translate_text("привет", "English"))
        finally:
            bot.client = previous_client
            bot.KYRGYZ_CONVERSATIONAL_MODE = previous_flag
        self.assertEqual("hello", result)
        self.assertNotIn("temperature", fake.calls[0])


if __name__ == "__main__":
    unittest.main()
