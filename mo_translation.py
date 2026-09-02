"""Helpers for an isolated conversational Russian <-> Moldovan pipeline.

The project calls the language ``mo`` in the UI.  In practice this is the
everyday Romanian/Moldovan used in Moldova; the model is asked to keep it
friendly and chat-like without sacrificing the meaning of the source.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping, Sequence

DATA_DIR = Path(__file__).with_name("data")
CONTEXT_LIMIT = 5
TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁёĂăÂâÎîȘșȚț]+", re.UNICODE)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.|t\.me/)\S+")
USERNAME_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{4,}")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
PERCENT_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%")
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b")
CODE_RE = re.compile(r"\b(?=[A-Za-z0-9_-]*[A-Za-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{4,}\b")
CURRENCY_RE = re.compile(r"(?i)(?<!\w)(?:USDT|TMT|RUB|USD|EUR|MDL|RON)(?!\w)")

MO_WORDS = {
    "salut", "bună", "buna", "frate", "bro", "ce", "faci", "unde", "când", "cand", "cât", "cat",
    "da", "nu", "acum", "mâine", "maine", "azi", "bani", "trimite", "trimiteți", "cont", "verific",
    "bine", "gata", "mulțumesc", "multumesc", "mersi", "ms", "te", "rog", "poate", "vreau", "lucru",
    "jucători", "jucatori", "scrie", "așteaptă", "asteapta", "de", "la", "pentru", "este", "e", "sunt",
    "aveți", "aveti", "puteți", "puteti", "vă", "va", "să", "sa", "care", "cum", "dece", "răspunzi",
    "raspunzi", "linkul", "cardul", "soldul", "retrage", "comision", "cod", "promo", "deschide", "contul",
}
RU_WORDS = {
    "брат", "будет", "вам", "вас", "где", "да", "давай", "деньги", "если", "есть", "как", "когда",
    "мне", "можно", "можешь", "надо", "нет", "нужно", "потом", "почему", "привет", "сейчас", "скинь",
    "сколько", "спасибо", "тебе", "ты", "уже", "что", "это", "я", "ответ", "пришли", "отправь",
}
FORMAL_MARKERS = {"bună ziua", "buna ziua", "vă rog", "va rog", "puteți", "puteti", "mulțumesc", "multumesc"}
SLANG_MARKERS = {"frate", "bro", "ms", "mersi", "acum", "ok", "hai", "ce faci", "buna", "salut"}


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().casefold() in {"1", "true", "yes", "on"}


def is_moldovan_language(language: str) -> bool:
    normalized = language.casefold().strip()
    return normalized.startswith(("moldovan", "moldovenească", "moldoveneasca", "romanian", "română", "romana")) or "молдав" in normalized


def tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def language_scores(text: str) -> tuple[int, int]:
    words = tokens(text)
    mo_score = sum(word in MO_WORDS for word in words)
    mo_score += len(re.findall(r"[ĂăÂâÎîȘșȚț]", text)) * 2
    ru_score = sum(word in RU_WORDS for word in words)
    return mo_score, ru_score


def looks_moldovan(text: str) -> bool:
    mo_score, ru_score = language_scores(text)
    return mo_score >= 2 or (mo_score >= 1 and not CYRILLIC_RE.search(text) and mo_score > ru_score)


def choose_direction(text: str) -> str:
    mo_score, ru_score = language_scores(text)
    if CYRILLIC_RE.search(text):
        return "ru_to_mo"
    if mo_score >= 2 and mo_score >= ru_score:
        return "mo_to_ru"
    return "mo_to_ru" if looks_moldovan(text) else "ru_to_mo"


def classify_style(text: str) -> str:
    lowered = text.casefold()
    words = tokens(text)
    if any(marker in lowered for marker in FORMAL_MARKERS):
        return "formal"
    if any(marker in lowered for marker in SLANG_MARKERS):
        return "slang"
    if len(words) <= 3:
        return "very_casual"
    if len(words) <= 12 or not re.search(r"[.!?]$", text.strip()):
        return "casual"
    return "neutral"


@lru_cache(maxsize=1)
def translation_examples() -> list[dict]:
    path = DATA_DIR / "mo_translation_examples.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _example_score(text: str, row: Mapping[str, str]) -> int:
    return len(set(tokens(text)) & set(tokens(row.get("source", "")))) * 10 - abs(len(tokens(text)) - len(tokens(row.get("source", ""))))


def retrieve_translation_examples(text: str, direction: str, limit: int = 4) -> list[dict]:
    target = "mo" if direction == "ru_to_mo" else "ru"
    rows = [row for row in translation_examples() if row.get("target_language") == target]
    return sorted(rows, key=lambda row: _example_score(text, row), reverse=True)[:limit]


def format_context(history: Sequence[Mapping[str, object]] | None) -> str:
    if not history:
        return ""
    lines = []
    for item in filter_history(history)[-CONTEXT_LIMIT:]:
        role = "client" if item["direction"] == "incoming" else "manager"
        value = str(item["text"]).strip().replace("\x00", "")[:500]
        if value:
            lines.append(f"[{role}] {value}")
    return (
        "Conversation context for meaning only. Use it only to resolve ambiguity in the current short message. "
        "Never translate these lines and never copy or add their information:\n" + "\n".join(lines) + "\n\n"
        if lines else ""
    )


def filter_history(history: Sequence[Mapping[str, object]] | None) -> list[Mapping[str, object]]:
    if not history:
        return []
    relevant = []
    for item in history:
        value = str(item["text"])
        if CYRILLIC_RE.search(value) or looks_moldovan(value):
            relevant.append(item)
    return relevant[-CONTEXT_LIMIT:]


def build_input(text: str, history: Sequence[Mapping[str, object]] | None = None) -> str:
    return format_context(history) + "Translate ONLY this message:\n" + text


def build_instructions(text: str, direction: str, style: str | None = None) -> str:
    style = style or classify_style(text)
    examples = retrieve_translation_examples(text, direction)
    example_lines = "\n".join(f"{row['source']} -> {row['target']}" for row in examples)
    common = (
        "PRIMARY PRIORITY: preserve the exact meaning of the current source message. Accuracy always comes before chat style. "
        "Do not add, remove, infer or change information, intent, question/statement form, negation, tense, person, pronouns or certainty. "
        "Understand typos, abbreviations, slang and short follow-ups. Use context only to resolve genuine ambiguity and never override a clear current message. "
        "Keep short messages short. Preserve every number, percentage, currency, username, URL, phone, date, promo code, name and emoji exactly. "
        "Do not intentionally worsen grammar. Return only the translation without labels, quotes or explanations."
    )
    if direction == "ru_to_mo":
        target = (
            "Translate Russian Telegram messages into natural everyday Moldovan/Romanian as people commonly write in Moldova. "
            "Use friendly conversational wording, not literary, bureaucratic or textbook language. Keep the original politeness and emotion. "
        )
    else:
        target = (
            "Translate Moldovan/Romanian Telegram messages (including Latin spelling without diacritics, typos, abbreviations and mixed chat speech) "
            "into clear natural conversational Russian in Cyrillic. Keep the result short and do not invent details. "
        )
    return target + f"Source style: {style}. {common}" + ("\n\nRelevant examples:\n" + example_lines if example_lines else "")


def protected_values(text: str) -> dict[str, Counter[str]]:
    def values(pattern: re.Pattern[str], normalize=lambda value: value) -> Counter[str]:
        return Counter(normalize(match.group(0)) for match in pattern.finditer(text))
    return {
        "numbers": values(NUMBER_RE, lambda value: value.replace(",", ".")),
        "percentages": values(PERCENT_RE, lambda value: value.replace(" ", "").replace(",", ".")),
        "urls": values(URL_RE), "usernames": values(USERNAME_RE, str.casefold),
        "phones": values(PHONE_RE, lambda value: re.sub(r"\D", "", value)), "dates": values(DATE_RE),
        "codes": values(CODE_RE, str.casefold), "currencies": values(CURRENCY_RE, str.casefold),
    }


def missing_or_changed_entities(source: str, translated: str) -> list[str]:
    source_values = protected_values(source)
    target_values = protected_values(translated)
    return [name for name, expected in source_values.items() if expected != target_values[name]]


def translation_needs_retry(source: str, translated: str, direction: str) -> list[str]:
    problems = missing_or_changed_entities(source, translated)
    if not translated.strip():
        problems.append("empty_output")
    if len(tokens(source)) <= 5 and len(tokens(translated)) > max(8, len(tokens(source)) * 3):
        problems.append("short_message_expanded")
    if direction == "mo_to_ru" and not CYRILLIC_RE.search(translated):
        problems.append("russian_not_cyrillic")
    if direction == "ru_to_mo" and CYRILLIC_RE.search(translated):
        problems.append("moldovan_contains_cyrillic")
    return sorted(set(problems))


def retry_instruction(problems: Iterable[str], direction: str) -> str:
    language = "natural conversational Moldovan/Romanian" if direction == "ru_to_mo" else "natural conversational Russian in Cyrillic"
    return (
        f"The previous result failed validation: {', '.join(problems)}. Translate again into {language}. "
        "Preserve exact meaning and copy every number percentage currency username URL phone date code and name exactly. "
        "Return only the corrected translation."
    )
