"""Small dependency-free checks for isolated Telegram translation context."""

import asyncio
import gc
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import bot


class FakeResponses:
    def __init__(self, output_text="what about tomorrow"):
        self.calls = []
        self.output_text = output_text

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class TranslationContextTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = bot.DB_PATH
        bot.DB_PATH = Path(self.temp_dir.name) / "translator.sqlite3"
        bot.init_db()

    def tearDown(self):
        bot.DB_PATH = self.previous_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_keeps_only_eight_messages_and_isolates_users(self):
        for number in range(12):
            bot.save_translation_history(1, 101, "incoming", f"message {number}")
        bot.save_translation_history(1, 202, "incoming", "other user's message")

        first_history = bot.recent_translation_history(1, 101)
        second_history = bot.recent_translation_history(1, 202)

        self.assertEqual(8, len(first_history))
        self.assertEqual("message 4", first_history[0]["text"])
        self.assertEqual(["other user's message"], [row["text"] for row in second_history])

    def test_short_follow_up_receives_previous_context(self):
        bot.save_translation_history(1, 101, "incoming", "он сегодня будет?")
        fake_responses = FakeResponses()
        previous_client = bot.client
        bot.client = SimpleNamespace(responses=fake_responses)
        try:
            result = asyncio.run(
                bot.translate_text(
                    "а завтра",
                    "English",
                    history=bot.recent_translation_history(1, 101),
                )
            )
        finally:
            bot.client = previous_client

        self.assertEqual("what about tomorrow", result)
        request_text = fake_responses.calls[0]["input"]
        self.assertIn("он сегодня будет?", request_text)
        self.assertIn("Current message to translate:\nа завтра", request_text)
        self.assertIn("Return only the translation", fake_responses.calls[0]["instructions"])

    def test_accuracy_prompt_and_supported_targets_are_explicit(self):
        targets = (
            "Русский",
            "Кыргызча (кыргызский)",
            "O‘zbekcha (lotin)",
            "Türkmençe (туркменский)",
            "Тоҷикӣ (таджикский)",
        )
        for target in targets:
            instructions = bot.translation_instruction(target, "casual")
            self.assertIn(target, instructions)
            self.assertIn("PRIMARY PRIORITY: preserve the exact meaning", instructions)
            self.assertIn("never let prior context override", instructions)
            self.assertNotIn("Do not deliberately fix", instructions)
            self.assertNotIn("overly correct", instructions)
        turkmen_instructions = bot.translation_instruction("Türkmençe (туркменский)", "casual")
        self.assertIn(bot.TURKMEN_OUTPUT_RULES, turkmen_instructions)
        self.assertIn("Never use Cyrillic", turkmen_instructions)
        self.assertIn("Do not use full stops, commas, question marks", turkmen_instructions)
        self.assertEqual("salam cay gowy", bot.plain_turkmen_latin("salam, cäy gowy."))
        self.assertEqual("Seyle", bot.plain_turkmen_latin("Şeýle"))
        self.assertEqual(
            "Salam brat nahili yagdaylaryn",
            bot.strict_turkmen_output("Salam, brat, nähili ýagdaýlaryň?"),
        )
        with self.assertRaises(RuntimeError):
            bot.strict_turkmen_output("Салам брат")
        self.assertTrue(bot.is_turkmen_language("Turkmen"))
        self.assertTrue(bot.is_turkmen_language("Türkmençe (туркменский)"))
        self.assertEqual(
            "sayta https://example.com/path giriw 2.5 USDT",
            bot.plain_turkmen_latin("sayta https://example.com/path, giriw 2.5 USDT."),
        )
        self.assertEqual(
            "depozitden 8% we pul cykarmagyndan 2% promokoddan 35% alarsynyz",
            bot.plain_turkmen_latin(
                "depozitden 8%, we pul çykarmagyndan 2%. promokoddan 35% alarsyňyz."
            ),
        )

    def test_manual_language_selection_is_explicit_despite_old_context(self):
        fake_responses = FakeResponses()
        previous_client = bot.client
        bot.client = SimpleNamespace(responses=fake_responses)
        try:
            asyncio.run(
                bot.translate_manual_chat(
                    "Что от меня нужно будет?",
                    "Türkmençe (туркменский)",
                    history=[{"direction": "outgoing", "text": "old English message"}],
                )
            )
        finally:
            bot.client = previous_client

        instructions = fake_responses.calls[0]["instructions"]
        self.assertIn("Türkmençe (туркменский)", instructions)
        self.assertIn("must never override a clear current message", instructions)

    def test_all_turkmen_translation_paths_apply_strict_chat_output(self):
        source_result = "Salam, brat, nähili ýagdaýlaryň?"
        expected = "Salam brat nahili yagdaylaryn"
        previous_client = bot.client
        try:
            bot.client = SimpleNamespace(responses=FakeResponses(source_result))
            self.assertEqual(
                expected,
                asyncio.run(bot.translate_text("Привет брат как дела?", "Türkmençe (туркменский)")),
            )

            bot.client = SimpleNamespace(responses=FakeResponses(source_result))
            self.assertEqual(
                expected,
                asyncio.run(bot.translate_text("Привет брат как дела?", "Turkmen")),
            )

            bot.client = SimpleNamespace(responses=FakeResponses(source_result))
            self.assertEqual(
                expected,
                asyncio.run(bot.translate_manual_chat("Привет брат как дела?", "Türkmençe (туркменский)")),
            )

            bot.client = SimpleNamespace(responses=FakeResponses("Russian\n" + source_result))
            language, translated = asyncio.run(
                bot.translate_incoming("Привет брат как дела?", "Türkmençe (туркменский)")
            )
            self.assertEqual("Russian", language)
            self.assertEqual(expected, translated)
        finally:
            bot.client = previous_client


if __name__ == "__main__":
    unittest.main()
