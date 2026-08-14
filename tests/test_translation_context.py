"""Small dependency-free checks for isolated Telegram translation context."""

import asyncio
import gc
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import bot


class FakeResponses:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="what about tomorrow")


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

    def test_keeps_only_ten_messages_and_isolates_users(self):
        for number in range(12):
            bot.save_translation_history(1, 101, "incoming", f"message {number}")
        bot.save_translation_history(1, 202, "incoming", "other user's message")

        first_history = bot.recent_translation_history(1, 101)
        second_history = bot.recent_translation_history(1, 202)

        self.assertEqual(10, len(first_history))
        self.assertEqual("message 2", first_history[0]["text"])
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


if __name__ == "__main__":
    unittest.main()
