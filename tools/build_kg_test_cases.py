"""Build a deterministic regression set from reviewed RU ↔ KY examples."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "kg_translation_examples.json"
OUTPUT = ROOT / "tests" / "kg_translation_cases.json"


def category(source: str, style: str) -> str:
    lowered = source.casefold()
    if re.search(r"\d", source):
        return "money" if any(value in lowered for value in ("сом", "usdt", "rub", "kgs")) else "numbers"
    if "?" in source or any(value in lowered.split() for value in ("сколько", "почему", "когда", "канча", "эмнеге", "качан")):
        return "questions"
    if any(value in lowered for value in ("скрин", "screenshot")):
        return "screenshots"
    if any(value in lowered for value in ("telegram", "ссылка", "аккаунт", "username", "id")):
        return "Telegram"
    if style == "formal":
        return "formal"
    if style == "slang" or "брат" in lowered:
        return "slang"
    if len(source.split()) == 1:
        return "one_word"
    if len(source.split()) <= 3:
        return "very_short"
    if any(value in lowered for value in ("не ", "жок", "эмес", "болбойт", "элек")):
        return "negative_statements"
    return "casual"


def main() -> None:
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    cases = []
    for index, row in enumerate(examples, 1):
        direction = "ru_to_ky" if row["target_language"] == "ky" else "ky_to_ru"
        cases.append({
            "id": f"base-{index:03d}",
            "direction": direction,
            "source": row["source"],
            "reference": row["target"],
            "style": row["style"],
            "category": "mixed_ru_ky" if row["source_language"] == "mixed_ru_ky" else category(row["source"], row["style"]),
        })

    # Emoji variants exercise preservation without inventing new translation pairs.
    for index, row in enumerate(examples[:25], 1):
        direction = "ru_to_ky" if row["target_language"] == "ky" else "ky_to_ru"
        cases.append({
            "id": f"emoji-{index:03d}",
            "direction": direction,
            "source": row["source"].rstrip(".!?") + " 🙂",
            "reference": row["target"].rstrip(".!?") + " 🙂",
            "style": row["style"],
            "category": "emoji",
        })

    # Context cases keep the current message short; context is understanding-only.
    context_rows = [
        ("ru_to_ky", ["он сегодня будет?"], "а завтра", "эртеңчи", "very_short"),
        ("ru_to_ky", ["деньги еще не пришли"], "а сейчас", "азырчы", "very_short"),
        ("ru_to_ky", ["скинь скрин"], "еще один", "дагы бирөө", "very_short"),
        ("ru_to_ky", ["он ответил"], "а она", "алчы", "very_short"),
        ("ru_to_ky", ["перевод будет завтра"], "точно?", "точнобу?", "questions"),
        ("ky_to_ru", ["ал бүгүн келет"], "эртеңчи", "а завтра?", "very_short"),
        ("ky_to_ru", ["акча түштү"], "канча", "сколько", "one_word"),
        ("ky_to_ru", ["скрин жибер"], "дагы", "еще", "one_word"),
        ("ky_to_ru", ["бул карта иштебейт"], "башкасы барбы", "есть другая?", "questions"),
        ("ky_to_ru", ["азыр текшерем"], "болду", "ладно", "one_word"),
    ]
    for index, (direction, context, source, reference, case_category) in enumerate(context_rows, 1):
        cases.append({
            "id": f"context-{index:03d}",
            "direction": direction,
            "source": source,
            "reference": reference,
            "style": "very_casual",
            "category": case_category,
            "context": context,
        })

    typo_rows = [
        ("ru_to_ky", "скин скрин", "скрин жибер", "typos"),
        ("ru_to_ky", "денги пришли", "акча түштүбү", "typos"),
        ("ru_to_ky", "щас проверюю", "азыр текшерем", "typos"),
        ("ru_to_ky", "прив брат", "салам брат", "typos"),
        ("ru_to_ky", "атправь сюда", "ушул жакка жибер", "typos"),
        ("ky_to_ru", "акча туштубу", "деньги пришли?", "typos"),
        ("ky_to_ru", "азр текшерем", "сейчас проверю", "typos"),
        ("ky_to_ru", "жиберч", "скинь пожалуйста", "typos"),
        ("ky_to_ru", "кайдасын", "ты где", "typos"),
        ("ky_to_ru", "тушунбодум", "не понял", "typos"),
    ]
    for index, (direction, source, reference, case_category) in enumerate(typo_rows, 1):
        cases.append({
            "id": f"typo-{index:03d}",
            "direction": direction,
            "source": source,
            "reference": reference,
            "style": "very_casual",
            "category": case_category,
        })

    no_punctuation = [row for row in examples if len(row["source"].split()) >= 4][:12]
    for index, row in enumerate(no_punctuation, 1):
        direction = "ru_to_ky" if row["target_language"] == "ky" else "ky_to_ru"
        cases.append({
            "id": f"nopunct-{index:03d}",
            "direction": direction,
            "source": re.sub(r"[.,!?]+", "", row["source"]).casefold(),
            "reference": re.sub(r"[.,!?]+", "", row["target"]).casefold(),
            "style": row["style"],
            "category": "no_punctuation",
        })

    required_rows = [
        ("ru_to_ky", "перевод уже отправил", "переводду жибергем", "transfers"),
        ("ky_to_ru", "500 сом котордум", "перевел 500 сом", "transfers"),
        ("ru_to_ky", "код 847291", "код 847291", "numbers"),
        ("ky_to_ru", "ID 739105 даяр", "ID 739105 готов", "numbers"),
        ("ru_to_ky", "отправь пожалуйста ссылку", "ссылканы жиберчи", "requests"),
        ("ky_to_ru", "скрин жиберчи", "скинь скрин пожалуйста", "requests"),
        ("ru_to_ky", "да уже готово", "ооба даяр", "answers"),
        ("ky_to_ru", "ооба болот", "да будет", "answers"),
    ]
    for index, (direction, source, reference, case_category) in enumerate(required_rows, 1):
        cases.append({
            "id": f"required-{index:03d}",
            "direction": direction,
            "source": source,
            "reference": reference,
            "style": "casual",
            "category": case_category,
        })

    holdout_pairs = [
        ("ты сейчас дома?", "азыр үйдөсүңбү?", "questions"),
        ("я через 10 минут приду", "10 мүнөттөн кийин барам", "numbers"),
        ("ему уже написал?", "ага жаздыңбы?", "questions"),
        ("пусть подождет немного", "бир аз күтүп турсун", "requests"),
        ("у тебя есть другая карта?", "башка картаң барбы?", "questions"),
        ("скинь номер карты", "карта номерин жиберчи", "requests"),
        ("не отправляй пока", "азырынча жибербе", "negative_statements"),
        ("я сам проверю", "өзүм текшерем", "casual"),
        ("потом созвонимся", "кийин сүйлөшөбүз", "casual"),
        ("ответ пока не пришел", "жооп али келе элек", "negative_statements"),
        ("сколько времени займет", "канча убакыт кетет", "questions"),
        ("можно сегодня сделать?", "бүгүн кылса болобу?", "questions"),
        ("он точно согласен?", "ал точно макулбу?", "mixed_ru_ky"),
        ("ничего не понял брат", "эч нерсе түшүнгөн жокмун брат", "slang"),
        ("сначала отправь скрин", "биринчи скрин жибер", "screenshots"),
        ("деньги вернутся на карту", "акча картага кайра түшөт", "money"),
        ("с баланса сняли 8%", "баланстан 8% алышты", "money"),
        ("отправь ровно 1200 сом", "точно 1200 сом жибер", "money"),
        ("мой ID 483920", "менин ID 483920", "numbers"),
        ("напиши @manager сейчас", "@manager ге азыр жаз", "Telegram"),
        ("открой https://t.me/example", "https://t.me/example ач", "Telegram"),
        ("завтра утром напомни", "эртең менен эскертип кой", "requests"),
        ("ща уточню у него", "азыр андан тактап алам", "slang"),
        ("да брат все четко", "ооба брат баары норм", "slang"),
        ("не бери трубку", "трубканы алба", "negative_statements"),
        ("он че сказал", "ал эмне деди", "slang"),
        ("просто жди", "жөн эле күт", "very_short"),
        ("это твой промокод A7K92", "бул сенин промокодуң A7K92", "Telegram"),
        ("заявка на 25 USDT готова", "25 USDT заявка даяр", "money"),
        ("пожалуйста не меняйте пароль", "парольду өзгөртпөй туруңузчу", "formal"),
    ]
    for index, (russian, kyrgyz, case_category) in enumerate(holdout_pairs, 1):
        shared = {
            "style": "formal" if case_category == "formal" else "casual",
            "category": case_category,
            "holdout": True,
        }
        cases.append({
            "id": f"holdout-ru-{index:03d}", "direction": "ru_to_ky",
            "source": russian, "reference": kyrgyz, **shared,
        })
        cases.append({
            "id": f"holdout-ky-{index:03d}", "direction": "ky_to_ru",
            "source": kyrgyz, "reference": russian, **shared,
        })

    OUTPUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {OUTPUT}")


if __name__ == "__main__":
    main()
