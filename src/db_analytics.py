"""
src/db_analytics.py

Analytics adapter that reads from ancient_names.db (SQLite) instead of JSON.
Returns the same flat-dict shape as src/analytics.compute_all() so that
dashboard.py can use it as a drop-in replacement.

Usage:
    from src.db_analytics import compute_all_from_db
    data = compute_all_from_db("ancient_names.db")
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from src.linguistics import (
    analyze_cluster_types,
    analyze_phonetic_classes,
    analyze_positions,
    analyze_sonority_slope,
    get_consonant_clusters,
    get_root_vowel,
)

VOWELS = set("aeiouāīūêâîûàèìò")


# ── helpers ────────────────────────────────────────────────────────────────────

def _open(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def _counter_from_query(con: sqlite3.Connection, sql: str, params=()) -> Counter:
    return Counter({row[0]: row[1] for row in con.execute(sql, params).fetchall()})


# ── main entry point ───────────────────────────────────────────────────────────

def compute_all_from_db(db_path: str) -> dict:
    """
    Query ancient_names.db and return the same result dict as analytics.compute_all().
    All values are plain Python — safe to pickle / @st.cache_data.
    """
    if not Path(db_path).exists():
        return {"db": [], "total": 0}

    con = _open(db_path)

    # ── corpus id ──────────────────────────────────────────────────────────────
    corpus_id = con.execute("SELECT id FROM corpora LIMIT 1").fetchone()[0]

    # ── total (Kassite corpus only) ────────────────────────────────────────────
    total = con.execute("SELECT COUNT(*) FROM names WHERE corpus_id = ?", (corpus_id,)).fetchone()[0]

    # ── phoneme inventory ──────────────────────────────────────────────────────
    consonants = _counter_from_query(con, """
        SELECT phoneme, count FROM phoneme_frequencies
        WHERE corpus_id = ? AND phoneme_class = 'consonant'
        ORDER BY count DESC
    """, (corpus_id,))

    vowels = _counter_from_query(con, """
        SELECT phoneme, count FROM phoneme_frequencies
        WHERE corpus_id = ? AND phoneme_class = 'vowel'
        ORDER BY count DESC
    """, (corpus_id,))

    bigrams = _counter_from_query(con, """
        SELECT bigram, count FROM bigram_frequencies
        WHERE corpus_id = ? ORDER BY count DESC
    """, (corpus_id,))

    # ── name structure ─────────────────────────────────────────────────────────
    name_lengths = _counter_from_query(con, """
        SELECT length_chars, COUNT(*) FROM name_morphology
        WHERE length_chars IS NOT NULL
        GROUP BY length_chars
    """)

    syllable_dist = _counter_from_query(con, """
        SELECT syllable_count, COUNT(*) FROM name_morphology
        WHERE syllable_count IS NOT NULL
        GROUP BY syllable_count
    """)

    cv_structures = _counter_from_query(con, """
        SELECT cv_structure, COUNT(*) FROM name_morphology
        WHERE cv_structure IS NOT NULL
        GROUP BY cv_structure ORDER BY COUNT(*) DESC
    """)

    # ── vowel positions ────────────────────────────────────────────────────────
    vowel_initial: Counter = Counter()
    vowel_medial: Counter  = Counter()
    vowel_final: Counter   = Counter()
    for row in con.execute("""
        SELECT phoneme, position, count FROM phoneme_position_stats
        WHERE corpus_id = ?
    """, (corpus_id,)).fetchall():
        ph, pos, cnt = row["phoneme"], row["position"], row["count"]
        if ph in VOWELS:
            if pos == "initial":
                vowel_initial[ph] = cnt
            elif pos == "medial":
                vowel_medial[ph]  = cnt
            elif pos == "final":
                vowel_final[ph]   = cnt

    # ── morphology ─────────────────────────────────────────────────────────────
    morpheme_roots    = _counter_from_query(con, """
        SELECT UPPER(SUBSTR(morpheme_root,1,1)) || LOWER(SUBSTR(morpheme_root,2)),
               COUNT(*)
        FROM name_morphology WHERE morpheme_root IS NOT NULL
        GROUP BY morpheme_root ORDER BY COUNT(*) DESC
    """)

    morpheme_suffixes = _counter_from_query(con, """
        SELECT LOWER(suffix), count FROM suffix_frequencies
        WHERE corpus_id = ? ORDER BY count DESC
    """, (corpus_id,))

    # suffix → roots and root → suffixes mappings (needed for morphology tab)
    suffix_to_roots: dict[str, list[str]]  = {}
    root_to_suffixes: dict[str, list[str]] = {}
    for row in con.execute("""
        SELECT morpheme_root, morpheme_suffix FROM name_morphology
        WHERE morpheme_root IS NOT NULL AND morpheme_suffix IS NOT NULL
    """).fetchall():
        r = row["morpheme_root"].capitalize()
        s = row["morpheme_suffix"].lower()
        if r not in suffix_to_roots.setdefault(s, []):
            suffix_to_roots[s].append(r)
        if s not in root_to_suffixes.setdefault(r, []):
            root_to_suffixes[r].append(s)

    root_productivity = {r: len(sl) for r, sl in root_to_suffixes.items()}

    # ── vowel correlation (root vowel → suffix vowel) ──────────────────────────
    vowel_correlation: Counter = Counter()
    for row in con.execute("""
        SELECT morpheme_root, morpheme_suffix FROM name_morphology
        WHERE morpheme_root IS NOT NULL AND morpheme_suffix IS NOT NULL
    """).fetchall():
        rv = get_root_vowel(row["morpheme_root"])
        if rv:
            vowel_correlation[f"{rv} → {row['morpheme_suffix'].lower()}"] += 1

    # ── consonant clusters & sonority ─────────────────────────────────────────
    consonant_clusters = _counter_from_query(con, """
        SELECT cluster, count FROM cluster_frequencies
        WHERE corpus_id = ? ORDER BY count DESC
    """, (corpus_id,))

    # cluster_types and sonority from DB cluster_class / sonority_direction
    cluster_types   = _counter_from_query(con, """
        SELECT cluster_class, SUM(count) FROM cluster_frequencies
        WHERE corpus_id = ? AND cluster_class IS NOT NULL
        GROUP BY cluster_class ORDER BY SUM(count) DESC
    """, (corpus_id,))

    sonority_stats  = _counter_from_query(con, """
        SELECT sonority_direction, SUM(count) FROM cluster_frequencies
        WHERE corpus_id = ? AND sonority_direction IS NOT NULL
        GROUP BY sonority_direction ORDER BY SUM(count) DESC
    """, (corpus_id,))

    # ── phonetic classes & initial/final consonants ───────────────────────────
    # These are derived from root text, so we compute them live from DB roots.
    phonetic_classes: Counter   = Counter()
    initial_consonants: Counter = Counter()
    final_consonants: Counter   = Counter()
    for row in con.execute("""
        SELECT initial_phoneme, final_phoneme, morpheme_root
        FROM name_morphology
        WHERE morpheme_root IS NOT NULL
    """).fetchall():
        root = row["morpheme_root"] or ""
        if len(root) >= 2:
            phonetic_classes.update(analyze_phonetic_classes(root))
            s, end = analyze_positions(root)
            if s and s not in VOWELS:
                initial_consonants[s] += 1
            if end and end not in VOWELS:
                final_consonants[end] += 1

    # ── theophoric ─────────────────────────────────────────────────────────────
    theophoric_counts = _counter_from_query(con, """
        SELECT canonical_name, name_count FROM v_deity_counts
    """)

    god_position_counts = _counter_from_query(con, """
        SELECT position, COUNT(*) FROM name_deity_links
        WHERE position IS NOT NULL
        GROUP BY position
    """)

    god_productivity = dict(con.execute("""
        SELECT canonical_name, unique_stems FROM v_deity_productivity
    """).fetchall())

    # ── variants & minimal pairs ───────────────────────────────────────────────
    # skeleton_variants: dict[skeleton → list[name_form]]
    skeleton_variants: dict[str, list[str]] = {}
    for row in con.execute("""
        SELECT svg.skeleton, svm.name_form
        FROM skeleton_variant_groups svg
        JOIN skeleton_variant_members svm ON svg.id = svm.group_id
        WHERE svg.corpus_id = ?
        ORDER BY svg.skeleton
    """, (corpus_id,)).fetchall():
        skeleton_variants.setdefault(row["skeleton"], []).append(row["name_form"])

    minimal_pairs: list[tuple[str, str]] = [
        (row["form_a"], row["form_b"])
        for row in con.execute("""
            SELECT form_a, form_b FROM minimal_pairs WHERE corpus_id = ?
        """, (corpus_id,)).fetchall()
    ]

    # ── cognate data ──────────────────────────────────────────────────────────
    # Known scholarly cognates from etymologies table
    known_cognates: list[dict] = []
    for row in con.execute("""
        SELECT e.form, l1.name AS kas_lang,
               e.proposed_meaning, l2.iso_code AS cog_lang_iso, l2.name AS cog_lang_name,
               e.cognate_form, e.confidence, e.scholarly_ref
        FROM etymologies e
        JOIN languages l1 ON e.language_id = l1.id
        JOIN languages l2 ON e.cognate_language_id = l2.id
        ORDER BY e.confidence DESC, e.form
    """).fetchall():
        known_cognates.append({
            "form":        row["form"],
            "cognate":     row["cognate_form"],
            "lang":        row["cog_lang_name"],
            "lang_iso":    row["cog_lang_iso"],
            "meaning":     row["proposed_meaning"],
            "confidence":  row["confidence"],
            "ref":         row["scholarly_ref"],
        })

    # Corpora available for cross-comparison
    all_corpora: list[dict] = []
    for row in con.execute("""
        SELECT c.id, c.name, l.iso_code, l.name AS lang_name,
               c.time_period_start, c.time_period_end, c.region,
               COUNT(n.id) AS name_count
        FROM corpora c
        JOIN languages l ON c.language_id = l.id
        LEFT JOIN names n ON n.corpus_id = c.id
        GROUP BY c.id
    """).fetchall():
        all_corpora.append({
            "id":         row["id"],
            "name":       row["name"],
            "iso":        row["iso_code"],
            "lang":       row["lang_name"],
            "start":      row["time_period_start"],
            "end":        row["time_period_end"],
            "region":     row["region"],
            "count":      row["name_count"],
        })

    # ── build `db` list for dashboard backward-compatibility ──────────────────
    # dashboard.py uses `db` for: theophoric flag, meaning count, LLM count,
    # and the deity-name browser in "Theophore Analyse".
    db: list[dict] = []
    for row in con.execute("""
        SELECT n.transcription, n.meaning,
               nm.cv_structure AS structure,
               nm.morpheme_root, nm.morpheme_suffix, nm.isolated_stem,
               vf.deity_names, vf.deity_position,
               n.llm_etymology, n.llm_semantic_field,
               n.llm_linguistic_notes, n.llm_comparable_forms, n.llm_confidence
        FROM names n
        LEFT JOIN name_morphology nm ON nm.name_id = n.id
        LEFT JOIN v_name_full vf ON vf.id = n.id
        WHERE n.corpus_id = ?
    """, (corpus_id,)).fetchall():
        deity_list = [d for d in (row["deity_names"] or "").split("||") if d]
        # deduplicate while preserving order
        seen: set[str] = set()
        unique_deities = [d for d in deity_list if not (d in seen or seen.add(d))]  # type: ignore[func-returns-value]
        llm = None
        if row["llm_etymology"]:
            import json as _json
            llm = {
                "etymology_hypothesis": row["llm_etymology"] or "",
                "semantic_field":       row["llm_semantic_field"] or "",
                "linguistic_notes":     row["llm_linguistic_notes"] or "",
                "comparable_forms":     _json.loads(row["llm_comparable_forms"] or "[]"),
                "confidence":           row["llm_confidence"] or "",
            }
        db.append({
            "transcription":  row["transcription"],
            "meaning":        row["meaning"] or "",
            "structure":      row["structure"] or "",
            "morpheme_root":  row["morpheme_root"] or "",
            "morpheme_suffix": row["morpheme_suffix"] or "",
            "isolated_stem":  row["isolated_stem"] or "",
            "detected_gods":  unique_deities,
            "god_position":   row["deity_position"] or "",
            "llm_analysis":   llm,
        })

    # ── LLM semantic fields & confidence distribution ──────────────────────────
    llm_semantic_fields: Counter = Counter()
    llm_confidence: Counter = Counter()
    for e in db:
        if e["llm_analysis"]:
            sf = e["llm_analysis"]["semantic_field"][:50].strip()
            if sf:
                llm_semantic_fields[sf] += 1
            conf = e["llm_analysis"]["confidence"]
            # Normalise confidence to short label
            conf_low = conf.lower()
            if "high" in conf_low:
                llm_confidence["High"] += 1
            elif "moderate" in conf_low and "low" not in conf_low:
                llm_confidence["Moderate"] += 1
            elif "low to moderate" in conf_low or "moderate to low" in conf_low:
                llm_confidence["Low–Moderate"] += 1
            else:
                llm_confidence["Low"] += 1

    # ── field coverage ─────────────────────────────────────────────────────────
    field_coverage = {
        "transcription":  total,
        "meaning":        sum(1 for e in db if e["meaning"]),
        "structure":      sum(1 for e in db if e["structure"]),
        "detected_gods":  sum(1 for e in db if e["detected_gods"]),
        "morpheme_root":  sum(1 for e in db if e["morpheme_root"]),
        "morpheme_suffix": sum(1 for e in db if e["morpheme_suffix"]),
        "isolated_stem":  sum(1 for e in db if e["isolated_stem"]),
        "llm_analysis":   sum(1 for e in db if e["llm_analysis"]),
    }

    # ── browser rows ───────────────────────────────────────────────────────────
    browser_rows = [
        {
            "Transkription":  e["transcription"],
            "Bedeutung":      e["meaning"],
            "Struktur":       e["structure"],
            "Morphem-Wurzel": e["morpheme_root"],
            "Morphem-Suffix": e["morpheme_suffix"],
            "Gottheiten":     ", ".join(e["detected_gods"]),
            "Stamm":          e["isolated_stem"],
            "Silben":         sum(1 for c in e["transcription"].lower() if c in VOWELS),
            "Länge":          len(e["transcription"].replace("-", "").replace(" ", "")),
        }
        for e in db
    ]

    con.close()

    return {
        # raw
        "db":               db,
        "total":            total,
        "field_coverage":   field_coverage,
        "browser_rows":     browser_rows,
        # phoneme
        "consonants":       consonants,
        "vowels":           vowels,
        "bigrams":          bigrams,
        # name structure
        "name_lengths":     name_lengths,
        "syllable_dist":    syllable_dist,
        "cv_structures":    cv_structures,
        "phonetic_classes": phonetic_classes,
        # vowels
        "vowel_initial":    vowel_initial,
        "vowel_medial":     vowel_medial,
        "vowel_final":      vowel_final,
        "vowel_correlation": vowel_correlation,
        # morphology
        "morpheme_roots":    morpheme_roots,
        "morpheme_suffixes": morpheme_suffixes,
        "suffix_to_roots":   suffix_to_roots,
        "root_to_suffixes":  root_to_suffixes,
        "root_productivity": root_productivity,
        # phonotactics
        "consonant_clusters":   consonant_clusters,
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
        # LLM
        "llm_semantic_fields": llm_semantic_fields,
        "llm_confidence":      llm_confidence,
        # cross-language / cognates
        "known_cognates": known_cognates,
        "all_corpora":    all_corpora,
    }
