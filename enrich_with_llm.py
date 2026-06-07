"""
Enriches the Kassite names database with LLM-generated linguistic analysis.

Usage:
    python enrich_with_llm.py               # enrich all un-analysed entries + synthesis
    python enrich_with_llm.py --limit 20    # process only first 20 entries
    python enrich_with_llm.py --force       # re-analyse already-enriched entries
    python enrich_with_llm.py --synthesis-only  # only regenerate the corpus synthesis

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here

Cost notes:
    - Per-name enrichment uses claude-haiku-4-5 (~$0.001 per name with caching)
    - Corpus synthesis uses claude-opus-4-6 with extended thinking (~$0.10)
"""

import argparse
import json
import os
import sys
import time

import anthropic

from src.llm_analyzer import analyze_name, build_corpus_stats, generate_corpus_synthesis

DB_PATH = "data/kassite_names_db_enriched.json"
SYNTHESIS_PATH = "output/corpus_synthesis.md"
SAVE_EVERY = 10  # save progress to disk after every N entries


def load_db() -> list:
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db: list) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def run_enrichment(client: anthropic.Anthropic, db: list, limit: int | None, force: bool) -> int:
    to_process = [
        (idx, entry) for idx, entry in enumerate(db)
        if force or not entry.get("llm_analysis")
    ]
    if limit:
        to_process = to_process[:limit]

    total = len(to_process)
    if total == 0:
        print("Nothing to process — all entries already enriched. Use --force to re-run.")
        return 0

    print(f"Enriching {total} entries with claude-haiku-4-5 (prompt caching active)...")
    errors = 0

    for batch_start in range(0, total, SAVE_EVERY):
        batch = to_process[batch_start : batch_start + SAVE_EVERY]

        for i, (db_idx, entry) in enumerate(batch):
            name = entry.get("transcription", "?")
            pos = batch_start + i + 1
            print(f"  [{pos:>4}/{total}] {name:<25}", end=" ", flush=True)

            try:
                analysis = analyze_name(client, entry)
                db[db_idx]["llm_analysis"] = {
                    "etymology_hypothesis": analysis.etymology_hypothesis,
                    "semantic_field":       analysis.semantic_field,
                    "linguistic_notes":     analysis.linguistic_notes,
                    "comparable_forms":     analysis.comparable_forms,
                    "confidence":           analysis.confidence,
                }
                print(f"[{analysis.confidence}] {analysis.semantic_field[:40]}")

            except anthropic.RateLimitError:
                print("rate-limited — waiting 30 s...")
                time.sleep(30)
                errors += 1
            except Exception as exc:
                print(f"ERROR: {exc}")
                errors += 1

        save_db(db)
        processed = batch_start + len(batch)
        print(f"  -> Saved ({processed}/{total} done, {errors} errors so far)")

    return total - errors


def run_synthesis(client: anthropic.Anthropic, db: list) -> None:
    print("\nGenerating corpus synthesis with claude-opus-4-6 + adaptive thinking...")
    stats = build_corpus_stats(db)
    synthesis = generate_corpus_synthesis(client, stats)

    os.makedirs("output", exist_ok=True)
    with open(SYNTHESIS_PATH, "w", encoding="utf-8") as f:
        f.write("# Kassitische Onomastik — Linguistische Korpus-Synthese\n\n")
        f.write("*Generiert mit Claude Opus (adaptive thinking) auf Basis von "
                f"{stats['total']} Belegen.*\n\n---\n\n")
        f.write(synthesis)

    print(f"[SUCCESS] Synthesis saved to '{SYNTHESIS_PATH}'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich Kassite names DB with LLM linguistic analysis"
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of entries to process")
    parser.add_argument("--force", action="store_true",
                        help="Re-analyse entries that already have llm_analysis")
    parser.add_argument("--synthesis-only", action="store_true",
                        help="Skip per-name enrichment; only regenerate corpus synthesis")
    parser.add_argument("--no-synthesis", action="store_true",
                        help="Skip synthesis generation after enrichment")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("  export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    db = load_db()
    print(f"Loaded {len(db)} entries from '{DB_PATH}'")

    if not args.synthesis_only:
        enriched = run_enrichment(client, db, args.limit, args.force)
        print(f"\n[DONE] {enriched} entries successfully enriched.")

    if not args.no_synthesis:
        run_synthesis(client, db)


if __name__ == "__main__":
    main()
