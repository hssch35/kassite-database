"""
src/analytics.py

Thin adapter between linguistics.py and the dashboard.
Reads the enriched JSON and runs every analysis, returning a single flat dict
of plain Python objects (Counter, dict, list) — no matplotlib, no Streamlit.

Usage:
    from src.analytics import compute_all
    data = compute_all("data/kassite_names_db_enriched.json")

Auto-reload pattern (in dashboard):
    mtime = os.path.getmtime(db_path)
    data  = load_data(db_path, mtime)   # @st.cache_data key includes mtime
"""

from __future__ import annotations

import json
import os
from collections import Counter

from src.linguistics import (
    analyze_bigrams,
    analyze_cluster_types,
    analyze_name_length,
    analyze_phoneme_inventory,
    analyze_phonetic_classes,
    analyze_positions,
    analyze_sonority_slope,
    analyze_syllable_distribution,
    analyze_theophoric_productivity,
    analyze_vowel_by_position,
    detect_consonantal_skeleton_variants,
    find_minimal_pairs,
    get_consonant_clusters,
    get_root_vowel,
)


def _load(db_path: str) -> list:
    if not os.path.exists(db_path):
        return []
    with open(db_path, encoding="utf-8") as f:
        return json.load(f)


def compute_all(db_path: str) -> dict:
    """
    Run every analysis on *db_path* and return a single results dict.
    All values are plain Python — safe to pickle / cache.
    """
    db = _load(db_path)
    if not db:
        return {"db": [], "total": 0}

    all_names = [e["transcription"] for e in db if e.get("transcription")]

    # ── Phoneme inventory ──────────────────────────────────────────────────
    consonants, vowels = analyze_phoneme_inventory(all_names)
    bigrams            = analyze_bigrams(all_names)
    name_lengths       = analyze_name_length(all_names)
    syllable_dist      = analyze_syllable_distribution(all_names)
    v_initial, v_medial, v_final = analyze_vowel_by_position(all_names)
    skeleton_variants  = detect_consonantal_skeleton_variants(all_names)
    minimal_pairs      = find_minimal_pairs(all_names)

    # ── Morphology (pre-computed fields in the DB) ─────────────────────────
    morpheme_roots    = [e["morpheme_root"].capitalize()
                         for e in db if e.get("morpheme_root")]
    morpheme_suffixes = [e["morpheme_suffix"].lower()
                         for e in db if e.get("morpheme_suffix")]
    cv_structures     = [e["structure"] for e in db if e.get("structure")]

    suffix_to_roots: dict[str, list[str]] = {}
    root_to_suffixes: dict[str, list[str]] = {}
    for e in db:
        r, s = e.get("morpheme_root"), e.get("morpheme_suffix")
        if r and s:
            r, s = r.capitalize(), s.lower()
            if r not in suffix_to_roots.setdefault(s, []):
                suffix_to_roots[s].append(r)
            if s not in root_to_suffixes.setdefault(r, []):
                root_to_suffixes[r].append(s)

    root_productivity = {r: len(sl) for r, sl in root_to_suffixes.items()}

    # ── Vowel correlation (root vowel → suffix vowel) ──────────────────────
    vowel_correlation: Counter = Counter()
    for e in db:
        root   = e.get("root")
        suffix = e.get("suffix")
        if root and suffix:
            rv = get_root_vowel(root)
            if rv:
                vowel_correlation[f"{rv} → {suffix}"] += 1

    # ── Consonant clusters & sonority ──────────────────────────────────────
    all_clusters: list[str] = []
    for e in db:
        stem = e.get("root") or e.get("morpheme_root") or ""
        all_clusters.extend(get_consonant_clusters(stem))

    cluster_counts  = Counter(all_clusters)
    cluster_types   = Counter(analyze_cluster_types(all_clusters))
    sonority_stats  = Counter(analyze_sonority_slope(all_clusters))

    # ── Phonetic classes, initial/final consonants ─────────────────────────
    phonetic_classes: Counter = Counter()
    initial_consonants: Counter = Counter()
    final_consonants: Counter  = Counter()
    for e in db:
        root = e.get("root") or ""
        if root and len(root) >= 2:
            phonetic_classes.update(analyze_phonetic_classes(root))
            s, end = analyze_positions(root)
            if s:
                initial_consonants[s] += 1
                final_consonants[end]  += 1

    # ── Theophoric analysis ────────────────────────────────────────────────
    theophoric_counts: Counter = Counter()
    god_position_counts: Counter = Counter()
    for e in db:
        for g in e.get("detected_gods", []):
            theophoric_counts[g] += 1
        if e.get("god_position"):
            god_position_counts[e["god_position"]] += 1

    god_productivity = analyze_theophoric_productivity(db)

    # ── LLM enrichment fields (optional) ──────────────────────────────────
    llm_semantic_fields: Counter = Counter()
    llm_confidence: Counter      = Counter()
    for e in db:
        la = e.get("llm_analysis") or {}
        if la.get("semantic_field"):
            llm_semantic_fields[la["semantic_field"]] += 1
        if la.get("confidence"):
            llm_confidence[la["confidence"]] += 1

    # ── Field coverage ─────────────────────────────────────────────────────
    tracked_fields = [
        "transcription", "meaning", "morphemes", "structure",
        "detected_gods", "isolated_stem", "morpheme_root",
        "morpheme_suffix", "root", "suffix", "llm_analysis",
    ]
    field_coverage = {k: sum(1 for e in db if e.get(k)) for k in tracked_fields}

    # ── Name-level DataFrame rows (for browser tab) ────────────────────────
    browser_rows = [
        {
            "Transkription":  e.get("transcription", ""),
            "Bedeutung":      e.get("meaning", ""),
            "Struktur":       e.get("structure", ""),
            "Morphem-Wurzel": e.get("morpheme_root", ""),
            "Morphem-Suffix": e.get("morpheme_suffix", ""),
            "Gottheiten":     ", ".join(e.get("detected_gods", [])),
            "Stamm":          e.get("isolated_stem") or "",
            "Silben":         len(__import__("re").findall(
                                  r"[aeiou]", (e.get("transcription") or "").lower())),
            "Länge":          len(__import__("re").sub(
                                  r"[\s\-]", "", (e.get("transcription") or "").lower())),
        }
        for e in db
    ]

    return {
        # raw
        "db":               db,
        "total":            len(db),
        "field_coverage":   field_coverage,
        "browser_rows":     browser_rows,
        # phoneme
        "consonants":       consonants,
        "vowels":           vowels,
        "bigrams":          bigrams,
        # name structure
        "name_lengths":     name_lengths,
        "syllable_dist":    syllable_dist,
        "cv_structures":    Counter(cv_structures),
        "phonetic_classes": phonetic_classes,
        # vowels
        "vowel_initial":     v_initial,
        "vowel_medial":      v_medial,
        "vowel_final":       v_final,
        "vowel_correlation": vowel_correlation,
        # morphology
        "morpheme_roots":    Counter(morpheme_roots),
        "morpheme_suffixes": Counter(morpheme_suffixes),
        "suffix_to_roots":   suffix_to_roots,
        "root_to_suffixes":  root_to_suffixes,
        "root_productivity": root_productivity,
        # phonotactics
        "consonant_clusters":   cluster_counts,
        "cluster_types":        cluster_types,
        "sonority_stats":       sonority_stats,
        "initial_consonants":   initial_consonants,
        "final_consonants":     final_consonants,
        # theophoric
        "theophoric_counts":    theophoric_counts,
        "god_position_counts":  god_position_counts,
        "god_productivity":     god_productivity,
        # variants
        "skeleton_variants": skeleton_variants,
        "minimal_pairs":     minimal_pairs,
        # LLM (may be empty)
        "llm_semantic_fields": llm_semantic_fields,
        "llm_confidence":      llm_confidence,
    }
