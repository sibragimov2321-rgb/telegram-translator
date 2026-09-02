"""Checks for the isolated Moldovan conversational translation profile."""

import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bot
import mo_translation as mo


class FakeResponses:
    def __init__(self, output_text="Salut frate ce faci?"):
        self.output_text = output_text
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class MoldovanPipelineTests(unittest.TestCase):
    def test_language_and_direction_detection(self):
        self.assertTrue(mo.is_moldovan_language("Moldovenească (молдавский)"))
        self.assertEqual("ru_to_mo", mo.choose_direction("Привет брат как дела?"))
        self.assertEqual("mo_to_ru", mo.choose_direction("Salut frate ce faci?"))

    def test_context_is_limited_to_moldovan_or_russian(self):
        history = [{"direction": "incoming", "text": "old English context"}]
        history += [{"direction": "incoming", "text": f"Unde esti {i}"} for i in range(8)]
        built = mo.build_input("dar maine", history)
        self.assertNotIn("old English context", built)
        self.assertIn("Unde esti 7", built)
        self.assertIn("Translate ONLY this message:\ndar maine", built)

    def test_prompt_prioritizes_meaning_and_chat_style(self):
        prompt = mo.build_instructions("Привет брат как дела?", "ru_to_mo")
        self.assertIn("PRIMARY PRIORITY", prompt)
        self.assertIn("exact meaning", prompt)
        self.assertIn("everyday Moldovan/Romanian", prompt)
        self.assertIn("not literary", prompt)
        self.assertIn("Return only the translation", prompt)

    def test_examples_and_protected_percentages(self):
        root = Path(__file__).resolve().parents[1]
        rows = json.loads((root / "data" / "mo_translation_examples.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(rows), 45)
        self.assertEqual([], mo.missing_or_changed_entities("Комиссия 8% и 350 EUR", "Comision 8% si 350 EUR"))

    def test_feature_flag_routes_moldovan_target_only(self):
        previous_flag = bot.MOLDOVAN_CONVERSATIONAL_MODE
        previous_translator = bot.translate_moldovan_conversational
        mocked = AsyncMock(return_value="Salut frate")
        bot.MOLDOVAN_CONVERSATIONAL_MODE = True
        bot.translate_moldovan_conversational = mocked
        try:
            result = asyncio.run(bot.translate_text("Привет брат", "Moldovenească (молдавский)"))
        finally:
            bot.MOLDOVAN_CONVERSATIONAL_MODE = previous_flag
            bot.translate_moldovan_conversational = previous_translator
        self.assertEqual("Salut frate", result)
        mocked.assert_awaited_once()

    def test_moldovan_translation_uses_retry_validation(self):
        previous_flag = bot.MOLDOVAN_CONVERSATIONAL_MODE
        previous_client = bot.client
        bot.MOLDOVAN_CONVERSATIONAL_MODE = True
        fake = FakeResponses("Comision 8% si 350 EUR")
        bot.client = SimpleNamespace(responses=fake)
        try:
            result = asyncio.run(bot.translate_text("Комиссия 8% и 350 EUR", "Moldovenească (молдавский)"))
        finally:
            bot.MOLDOVAN_CONVERSATIONAL_MODE = previous_flag
            bot.client = previous_client
        self.assertEqual("Comision 8% si 350 EUR", result)
        self.assertEqual(1, len(fake.calls))


if __name__ == "__main__":
    unittest.main()
