"""Build a deterministic 200+ case regression set for Russian ↔ Turkmen."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "tm_translation_examples.json"
OUTPUT = ROOT / "tests" / "tm_translation_cases.json"


def category(source: str, style: str) -> str:
    lowered = source.casefold()
    if re.search(r"\d", source):
        return "money" if any(value in lowered for value in ("tmt", "usdt", "rub", "%")) else "numbers"
    if any(value in lowered for value in ("vpn", "telegram", "ssyl", "ссыл", "username", "@")):
        return "Telegram"
    if any(value in lowered for value in ("скрин", "skrin", "screenshot")):
        return "screenshots"
    if any(value in lowered for value in ("игрок", "oyunc", "ставк", "ut")):
        return "casino"
    if any(value in lowered for value in ("промо", "promo")):
        return "promo"
    if "?" in source or any(value in lowered.split() for value in ("сколько", "почему", "когда", "nace", "name", "hacan")):
        return "questions"
    if style == "formal":
        return "formal"
    if style == "slang" or any(value in lowered for value in ("брат", "brat", "agam", "jigim")):
        return "slang"
    if len(source.split()) == 1:
        return "one_word"
    if len(source.split()) <= 3:
        return "very_short"
    return "casual"


def add(cases: list[dict], prefix: str, direction: str, source: str, reference: str, case_category: str, *, context=None, holdout=False) -> None:
    cases.append({
        "id": f"{prefix}-{len(cases)+1:03d}", "direction": direction, "source": source,
        "reference": reference, "style": "casual", "category": case_category,
        **({"context": context} if context else {}), **({"holdout": True} if holdout else {}),
    })


def main() -> None:
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    cases: list[dict] = []
    for index, row in enumerate(examples, 1):
        direction = "ru_to_tm" if row["target_language"] == "tm" else "tm_to_ru"
        cases.append({
            "id": f"base-{index:03d}", "direction": direction, "source": row["source"],
            "reference": row["target"], "style": row["style"],
            "category": category(row["source"], row["style"]),
        })

    for index, row in enumerate(examples[:25], 1):
        direction = "ru_to_tm" if row["target_language"] == "tm" else "tm_to_ru"
        cases.append({
            "id": f"emoji-{index:03d}", "direction": direction,
            "source": row["source"].rstrip(".!?") + " 🙂", "reference": row["target"].rstrip(".!?") + " 🙂",
            "style": row["style"], "category": "emoji",
        })

    context_rows = [
        ("ru_to_tm", ["он сегодня будет"], "а завтра", "ertir name", "very_short"),
        ("ru_to_tm", ["деньги еще не пришли"], "а сейчас", "hazir name", "very_short"),
        ("ru_to_tm", ["скинь скрин"], "еще один", "yene birini", "very_short"),
        ("ru_to_tm", ["он ответил"], "а она", "ol gyz name", "very_short"),
        ("ru_to_tm", ["перевод будет завтра"], "точно", "anykmy", "very_short"),
        ("tm_to_ru", ["ol su gun geler"], "ertir name", "а завтра", "very_short"),
        ("tm_to_ru", ["pul geldi"], "nace", "сколько", "one_word"),
        ("tm_to_ru", ["skrin ugrat"], "yene", "еще", "one_word"),
        ("tm_to_ru", ["bu karta bolanok"], "baskasy barmy", "есть другая", "questions"),
        ("tm_to_ru", ["hazir barlaryn"], "bolya", "ладно", "one_word"),
    ]
    for direction, context, source, reference, case_category in context_rows:
        add(cases, "context", direction, source, reference, case_category, context=context)

    typo_rows = [
        ("ru_to_tm", "скин скрин", "skrin ugrat"), ("ru_to_tm", "денги пришли", "pul geldimi"),
        ("ru_to_tm", "щас проверюю", "hazir barlaryn"), ("ru_to_tm", "прив брат", "salam brat"),
        ("ru_to_tm", "атправь сюда", "suna ugrat"), ("tm_to_ru", "pul geldmy", "деньги пришли"),
        ("tm_to_ru", "hazr barlaryn", "сейчас проверю"), ("tm_to_ru", "ugrat br", "отправь брат"),
        ("tm_to_ru", "sen nerde", "ты где"), ("tm_to_ru", "dusnmedim", "не понял"),
    ]
    for direction, source, reference in typo_rows:
        add(cases, "typo", direction, source, reference, "typos")

    for row in [value for value in examples if len(value["source"].split()) >= 4][:15]:
        direction = "ru_to_tm" if row["target_language"] == "tm" else "tm_to_ru"
        add(cases, "nopunct", direction, re.sub(r"[.,!?]+", "", row["source"]).casefold(), re.sub(r"[.,!?]+", "", row["target"]).casefold(), "no_punctuation")

    required = [
        ("ru_to_tm", "отправь ровно 350 TMT", "350 TMT ugrat", "money"),
        ("tm_to_ru", "350 TMT ugratdym", "отправил 350 TMT", "money"),
        ("ru_to_tm", "комиссия 8% и вывод 2%", "komissiya 8% we cykarys 2%", "money"),
        ("tm_to_ru", "depozit 8% cykarys 2%", "депозит 8% вывод 2%", "money"),
        ("ru_to_tm", "напиши @manager", "@manager yaz", "Telegram"),
        ("tm_to_ru", "https://t.me/example ac", "открой https://t.me/example", "Telegram"),
        ("ru_to_tm", "пришли скрин из VPN", "VPN den skrin ugrat", "screenshots"),
        ("tm_to_ru", "promo kod A7K92", "промокод A7K92", "promo"),
        ("ru_to_tm", "игрок выиграет", "oyuncy utar", "casino"),
        ("tm_to_ru", "oyuncym utan yagdaynda", "когда мой игрок выиграет", "casino"),
    ]
    for direction, source, reference, case_category in required:
        add(cases, "required", direction, source, reference, case_category)

    holdout_pairs = [
        ("ты сейчас дома", "sen hazir oyde", "questions"),
        ("я через 10 минут приду", "10 minutdan bararyn", "numbers"),
        ("ему уже написал", "ona yazdynmy", "questions"),
        ("пусть немного подождет", "azajyk garassyn", "requests"),
        ("у тебя есть другая карта", "sende baska karta barmy", "questions"),
        ("скинь номер карты", "karta nomerini ugrat", "requests"),
        ("пока не отправляй", "hazirlikce ugratma", "negative"),
        ("я сам проверю", "ozum barlaryn", "casual"),
        ("потом поговорим", "son gurrun ederis", "casual"),
        ("ответ еще не пришел", "jogap entek gelenok", "negative"),
        ("сколько времени займет", "nace wagt gerek", "questions"),
        ("можно сегодня сделать", "su gun edip bolarmy", "questions"),
        ("он точно согласен", "ol anyk razymy", "questions"),
        ("ничего не понял брат", "hic zat dusunmedim brat", "slang"),
        ("сначала отправь скрин", "ilki skrin ugrat", "screenshots"),
        ("деньги вернутся на карту", "pul karta gaydyp geler", "money"),
        ("с баланса сняли 8%", "balansdan 8% alyndy", "money"),
        ("отправь ровно 1200 TMT", "1200 TMT ugrat", "money"),
        ("мой ID 483920", "menin ID im 483920", "numbers"),
        ("напиши @manager сейчас", "hazir @manager yaz", "Telegram"),
        ("открой https://t.me/example", "https://t.me/example ac", "Telegram"),
        ("завтра утром напомни", "ertir irden yatlat", "requests"),
        ("ща уточню у него", "hazir ondan soraryn", "slang"),
        ("да брат все нормально", "howwa brat hemme zat normal", "slang"),
        ("не бери трубку", "telefony alma", "negative"),
        ("он что сказал", "ol name diydi", "questions"),
        ("просто жди", "garas", "very_short"),
        ("это твой промокод A7K92", "bu senin promokodyn A7K92", "promo"),
        ("заявка на 25 USDT готова", "25 USDT arza tayyar", "money"),
        ("пожалуйста не меняйте пароль", "hayys paroly uytgetman", "formal"),
    ]
    for russian, turkmen, case_category in holdout_pairs:
        add(cases, "holdout-ru", "ru_to_tm", russian, turkmen, case_category, holdout=True)
        add(cases, "holdout-tm", "tm_to_ru", turkmen, russian, case_category, holdout=True)

    OUTPUT.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {OUTPUT}")


if __name__ == "__main__":
    main()
