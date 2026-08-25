"""Compare the existing and conversational Kyrgyz prompts on curated cases."""

from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bot  # noqa: E402
import kg_translation as kg  # noqa: E402


def normalized(text: str) -> str:
    return " ".join(text.casefold().strip(" .,!?:;…").split())


def similarity(value: str, reference: str) -> float:
    return round(difflib.SequenceMatcher(None, normalized(value), normalized(reference)).ratio(), 4)


def choose_balanced(rows: list[dict], limit: int) -> list[dict]:
    selected: list[dict] = []
    counts: Counter[tuple[str, str]] = Counter()
    remaining = rows[:]
    while remaining and len(selected) < limit:
        remaining.sort(key=lambda row: (counts[(row["direction"], row["category"])], row["id"]))
        row = remaining.pop(0)
        selected.append(row)
        counts[(row["direction"], row["category"])] += 1
    return selected


async def evaluate_case(row: dict, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        history = [
            {"direction": "incoming", "text": value}
            for value in row.get("context", [])
        ]
        old_target = "Кыргызча (кыргызский)" if row["direction"] == "ru_to_ky" else "Русский"
        started = time.monotonic()
        try:
            old = await bot._translate_text_legacy(row["source"], old_target, "casual", history)
            old_error = ""
        except Exception as error:
            old = ""
            old_error = type(error).__name__
        old_seconds = time.monotonic() - started

        started = time.monotonic()
        try:
            new = await bot.translate_kyrgyz_conversational(row["source"], row["direction"], history)
            new_error = ""
        except Exception as error:
            new = ""
            new_error = type(error).__name__
        new_seconds = time.monotonic() - started

        source_words = max(1, len(kg.tokens(row["source"])))
        return {
            **row,
            "current": old,
            "new": new,
            "current_error": old_error,
            "new_error": new_error,
            "current_reference_similarity": similarity(old, row["reference"]) if old else 0,
            "new_reference_similarity": similarity(new, row["reference"]) if new else 0,
            "current_entity_errors": kg.missing_or_changed_entities(row["source"], old) if old else ["empty"],
            "new_entity_errors": kg.missing_or_changed_entities(row["source"], new) if new else ["empty"],
            "current_length_ratio": round(len(kg.tokens(old)) / source_words, 3) if old else 0,
            "new_length_ratio": round(len(kg.tokens(new)) / source_words, 3) if new else 0,
            "current_seconds": round(old_seconds, 3),
            "new_seconds": round(new_seconds, 3),
        }


def summary(results: list[dict]) -> dict:
    return {
        "cases": len(results),
        "current_errors": sum(bool(row["current_error"]) for row in results),
        "new_errors": sum(bool(row["new_error"]) for row in results),
        "current_entity_safe": sum(not row["current_entity_errors"] for row in results),
        "new_entity_safe": sum(not row["new_entity_errors"] for row in results),
        "current_average_reference_similarity": round(statistics.mean(row["current_reference_similarity"] for row in results), 4),
        "new_average_reference_similarity": round(statistics.mean(row["new_reference_similarity"] for row in results), 4),
        "current_average_seconds": round(statistics.mean(row["current_seconds"] for row in results), 3),
        "new_average_seconds": round(statistics.mean(row["new_seconds"] for row in results), 3),
        "new_closer_to_reference": sum(
            row["new_reference_similarity"] > row["current_reference_similarity"] for row in results
        ),
        "current_closer_to_reference": sum(
            row["current_reference_similarity"] > row["new_reference_similarity"] for row in results
        ),
        "equal_reference_similarity": sum(
            row["current_reference_similarity"] == row["new_reference_similarity"] for row in results
        ),
    }


def markdown_report(report: dict) -> str:
    stats = report["summary"]
    lines = [
        "# Kyrgyz translation OLD → NEW evaluation",
        "",
        f"Model: `{bot.MODEL}`",
        f"Cases: {stats['cases']}",
        "",
        "## Automated summary",
        "",
        f"- Current errors: {stats['current_errors']}",
        f"- New errors: {stats['new_errors']}",
        f"- Current entity-safe: {stats['current_entity_safe']}/{stats['cases']}",
        f"- New entity-safe: {stats['new_entity_safe']}/{stats['cases']}",
        f"- Current average reference similarity: {stats['current_average_reference_similarity']}",
        f"- New average reference similarity: {stats['new_average_reference_similarity']}",
        f"- New closer to curated reference: {stats['new_closer_to_reference']}",
        f"- Current closer to curated reference: {stats['current_closer_to_reference']}",
        f"- Current average latency: {stats['current_average_seconds']} s",
        f"- New average latency: {stats['new_average_seconds']} s",
        "",
        "Reference similarity is only a regression signal; it does not prove linguistic quality by itself.",
        "",
        "## Side-by-side cases",
        "",
    ]
    for index, row in enumerate(report["results"], 1):
        lines.extend([
            f"### {index}. {row['id']} — {row['direction']} / {row['category']}",
            "",
            f"SOURCE: {row['source']}",
            "",
            f"REFERENCE: {row['reference']}",
            "",
            f"CURRENT: {row['current'] or '[ERROR: ' + row['current_error'] + ']'}",
            "",
            f"NEW: {row['new'] or '[ERROR: ' + row['new_error'] + ']'}",
            "",
        ])
    return "\n".join(lines)


async def run(limit: int, concurrency: int, output_dir: Path, retry_errors: bool = False) -> None:
    rows = json.loads((ROOT / "tests" / "kg_translation_cases.json").read_text(encoding="utf-8"))
    holdout_rows = [row for row in rows if row.get("holdout")]
    if len(holdout_rows) >= limit:
        rows = holdout_rows
    report_path = output_dir / "kg_evaluation.json"
    previous_results: list[dict] = []
    if retry_errors and report_path.exists():
        previous_results = json.loads(report_path.read_text(encoding="utf-8"))["results"]
        failed_ids = {
            row["id"] for row in previous_results if row["current_error"] or row["new_error"]
        }
        selected = [row for row in rows if row["id"] in failed_ids]
    else:
        selected = choose_balanced(rows, limit)
    semaphore = asyncio.Semaphore(concurrency)
    refreshed = await asyncio.gather(*(evaluate_case(row, semaphore) for row in selected))
    if previous_results:
        refreshed_by_id = {row["id"]: row for row in refreshed}
        results = [refreshed_by_id.get(row["id"], row) for row in previous_results]
    else:
        results = refreshed
    report = {"summary": summary(results), "results": results}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "kg_evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "kg_evaluation.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.concurrency, args.output_dir, args.retry_errors))


if __name__ == "__main__":
    main()
