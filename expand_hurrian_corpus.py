"""
expand_hurrian_corpus.py

Adds additional Hurrian personal names from the Nuzi archive (Cassin & Glassner 1977,
Weeks 1983, Negri Scafa 1999, Wilhelm 1989) to the existing Hurrian corpus in ancient_names.db.

These names are selected for:
  - Tešup-theophoric compounds (major Hurrian storm god)
  - Šauška-theophoric compounds (Hurrian Ishtar)
  - Mitanni royal names relevant to Kassite cross-comparison
  - Nuzi administrative personnel (provide sociolinguistic context)
"""

import sqlite3
from collections import Counter

from src.linguistics import (
    analyze_phoneme_inventory,
    analyze_bigrams,
    analyze_syllable_distribution,
    analyze_vowel_by_position,
    get_consonant_clusters,
    analyze_cluster_types,
    analyze_sonority_slope,
    analyze_positions,
    detect_consonantal_skeleton_variants,
    find_minimal_pairs,
    discover_suffixes,
)

DB_PATH = "ancient_names.db"

# ---------------------------------------------------------------------------
# New Hurrian names to add
# (transcription, meaning_hint, source_note)
# ---------------------------------------------------------------------------

NEW_HURRIAN_NAMES: list[tuple[str, str, str]] = [
    # Tešup-theophoric (Nuzi archive)
    ("Teš-šub-seri",    "Tešup is my king",            "Cassin & Glassner 1977:114"),
    ("Ḫutil-Tešup",     "Protection of Tešup",          "Cassin & Glassner 1977:87"),
    ("Ewri-Tešup",      "Lord is Tešup",                "Weeks 1983:62"),
    ("Nai-Tešup",       "Grace of Tešup",               "Negri Scafa 1999:44"),
    ("Alki-Tešup",      "Strong is Tešup",              "Negri Scafa 1999:22"),
    ("Pahi-Tešup",      "Clan/face of Tešup",           "Negri Scafa 1999:55"),
    ("Šarri-Tešup",     "King is Tešup",                "Cassin & Glassner 1977:105"),
    ("Ziga-Tešup",      "Pure/holy Tešup",              "Cassin & Glassner 1977:127"),
    ("Tišam-Tešup",     "Tešup hears",                  "Weeks 1983:80"),
    ("Tulup-Tešup",     "Triumph of Tešup",             "Negri Scafa 1999:66"),
    ("Azzu-Tešup",      "Strong one of Tešup",          "Cassin & Glassner 1977:43"),
    ("Kiru-Tešup",      "Gesture/deed of Tešup",        "Cassin & Glassner 1977:92"),

    # Šauška-theophoric (Hurrian Ishtar)
    ("Šauška-taše",     "Beloved of Šauška",            "Wilhelm 1989:34"),
    ("Šauška-atal",     "Hero of Šauška",               "Cassin & Glassner 1977:107"),
    ("Ari-Šauška",      "Gift of Šauška",               "Weeks 1983:31"),
    ("Puhi-Šauška",     "Face/presence of Šauška",      "Negri Scafa 1999:57"),
    ("Kili-Šauška",     "Perfection of Šauška",         "Cassin & Glassner 1977:91"),

    # Mitanni royal and aristocratic names
    ("Parsasatar",      "Chariot-lord (royal name variant)", "Mayrhofer 1974:14"),
    ("Suttarna",        "Warrior king (< *Su-tarna)",    "Mayrhofer 1974:22"),
    ("Artatama",        "Righteous in truth",            "Mayrhofer 1974:10"),
    ("Tushratta",       "His chariot is great",          "Mayrhofer 1974:26"),
    ("Artama",          "Righteous (short form)",        "Wilhelm 1989:12"),
    ("Biridashwa",      "Noble / swift horse",           "Mayrhofer 1974:11"),
    ("Kirta",           "Name-bearer / famous",          "Cassin & Glassner 1977:92"),

    # Common Nuzi administrative names (men)
    ("Akiya",           "My brother (?)",               "Cassin & Glassner 1977:18"),
    ("Ari-ya",          "Given",                        "Cassin & Glassner 1977:30"),
    ("Baltu-ya",        "Life/vigor (Semitic component)","Negri Scafa 1999:26"),
    ("Enna-Tešup",      "Grace of Tešup",               "Cassin & Glassner 1977:64"),
    ("Ḫamanna",         "Weapon (?)",                   "Weeks 1983:58"),
    ("Ḫuya",            "Living / alive",               "Cassin & Glassner 1977:88"),
    ("Itḫip-šarri",     "Saved by the king",            "Negri Scafa 1999:40"),
    ("Muš-apu",         "Tamed one",                    "Cassin & Glassner 1977:102"),
    ("Nūr-Adad",        "Light of Adad (Semitic loanword)", "Cassin & Glassner 1977:104"),
    ("Sekar-Tilla",     "Fortune of Tilla",             "Weeks 1983:74"),
    ("Šelwiya",         "Sound/healthy",                "Negri Scafa 1999:62"),
    ("Tupkiya",         "Tablet (official)",            "Cassin & Glassner 1977:119"),
    ("Unap-tae",        "Gracious Tae-deity",           "Cassin & Glassner 1977:122"),
    ("Wir-šarri",       "Hero of the king",             "Weeks 1983:85"),
    ("Zike",            "Of the clan",                  "Cassin & Glassner 1977:126"),

    # Hurrian women's names (Nuzi)
    ("Šati-Šauška",     "Daughter of Šauška",           "Wilhelm 1989:55"),
    ("Tulpan-naya",     "Variant: flower / blossom",    "Cassin & Glassner 1977:120"),
    ("Ḫišmit-kušuḫ",   "Moonlit grace",                "Weeks 1983:61"),
    ("Nawar-Tešup",     "Light of Tešup",               "Negri Scafa 1999:48"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_cv_structure(name: str) -> str:
    VOWELS = set("aeiouāīūêâîûàèìò")
    clean = name.lower().replace("-", "").replace(" ", "")
    return "".join("V" if c in VOWELS else "C" for c in clean if c.isalpha() or c in VOWELS)


def _count_syllables(name: str) -> int:
    VOWELS = set("aeiouāīūêâîûàèìò")
    return sum(1 for c in name.lower() if c in VOWELS)


def _initial_phoneme(name: str) -> str:
    clean = name.replace("-", "").replace(" ", "")
    return clean[0].lower() if clean else ""


def _final_phoneme(name: str) -> str:
    clean = name.replace("-", "").replace(" ", "")
    return clean[-1].lower() if clean else ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def expand(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    # Get Hurrian corpus and language ids
    row = con.execute("""
        SELECT c.id, l.id FROM corpora c
        JOIN languages l ON c.language_id = l.id
        WHERE l.iso_code = 'hur'
    """).fetchone()
    if not row:
        print("ERROR: Hurrian corpus not found in DB.")
        return
    hur_corpus_id, hur_lang_id = row

    # Collect existing transcriptions to avoid duplicates
    existing = {
        r[0].lower()
        for r in con.execute(
            "SELECT transcription FROM names WHERE corpus_id = ?", (hur_corpus_id,)
        ).fetchall()
    }
    print(f"Existing Hurrian names: {len(existing)}")

    # ── Insert new names ──────────────────────────────────────────────────
    added = 0
    for transcription, meaning, source_note in NEW_HURRIAN_NAMES:
        if transcription.lower() in existing:
            continue  # skip duplicates

        clean = transcription.replace("-", "").replace(" ", "")
        cv_struct = _compute_cv_structure(transcription)
        n_syllables = _count_syllables(transcription)

        # Insert into names
        cur = con.execute(
            """INSERT INTO names (corpus_id, transcription, meaning)
               VALUES (?,?,?)""",
            (hur_corpus_id, transcription, meaning),
        )
        name_id = cur.lastrowid

        # Insert into name_morphology
        parts = transcription.split("-")
        root = parts[0] if parts else transcription
        suffix = parts[-1] if len(parts) > 1 else None

        con.execute(
            """INSERT OR IGNORE INTO name_morphology
               (name_id, morpheme_root, morpheme_suffix, isolated_stem,
                cv_structure, syllable_count, length_chars,
                initial_phoneme, final_phoneme)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                name_id, root, suffix, root,
                cv_struct, n_syllables, len(clean),
                _initial_phoneme(transcription),
                _final_phoneme(transcription),
            ),
        )

        existing.add(transcription.lower())
        added += 1

    con.commit()
    print(f"Added {added} new Hurrian names.")

    # ── Recompute corpus statistics ───────────────────────────────────────
    print("Recomputing Hurrian corpus statistics …")
    all_names = [
        r[0]
        for r in con.execute(
            "SELECT transcription FROM names WHERE corpus_id = ?", (hur_corpus_id,)
        ).fetchall()
    ]

    # Clear old stats
    con.execute("DELETE FROM phoneme_frequencies WHERE corpus_id = ?", (hur_corpus_id,))
    con.execute("DELETE FROM bigram_frequencies WHERE corpus_id = ?", (hur_corpus_id,))
    con.execute("DELETE FROM cluster_frequencies WHERE corpus_id = ?", (hur_corpus_id,))
    con.execute("DELETE FROM suffix_frequencies WHERE corpus_id = ?", (hur_corpus_id,))
    # Delete members first (FK child), then groups (FK parent)
    for grp_id, in con.execute(
        "SELECT id FROM skeleton_variant_groups WHERE corpus_id = ?", (hur_corpus_id,)
    ).fetchall():
        con.execute("DELETE FROM skeleton_variant_members WHERE group_id = ?", (grp_id,))
    con.execute("DELETE FROM skeleton_variant_groups WHERE corpus_id = ?", (hur_corpus_id,))

    # Phoneme frequencies
    cons_c, vow_c = analyze_phoneme_inventory(all_names)
    for ph, cnt in cons_c.items():
        con.execute(
            "INSERT INTO phoneme_frequencies (corpus_id, phoneme, phoneme_class, count) VALUES (?,?,?,?)",
            (hur_corpus_id, ph, "consonant", cnt),
        )
    for ph, cnt in vow_c.items():
        con.execute(
            "INSERT INTO phoneme_frequencies (corpus_id, phoneme, phoneme_class, count) VALUES (?,?,?,?)",
            (hur_corpus_id, ph, "vowel", cnt),
        )

    # Bigrams
    for bg, cnt in analyze_bigrams(all_names).items():
        con.execute(
            "INSERT INTO bigram_frequencies (corpus_id, bigram, count) VALUES (?,?,?)",
            (hur_corpus_id, bg, cnt),
        )

    # Clusters (get_consonant_clusters takes a single string, not a list)
    all_clusters: list[str] = []
    for name in all_names:
        all_clusters.extend(get_consonant_clusters(name))
    cluster_counts = Counter(all_clusters)
    for cl, cnt in cluster_counts.items():
        con.execute(
            "INSERT INTO cluster_frequencies (corpus_id, cluster, count) VALUES (?,?,?)",
            (hur_corpus_id, cl, cnt),
        )

    # Suffixes
    for suf, cnt in discover_suffixes(all_names).items():
        con.execute(
            "INSERT INTO suffix_frequencies (corpus_id, suffix, count) VALUES (?,?,?)",
            (hur_corpus_id, suf, cnt),
        )

    # Skeleton variants
    for skeleton, variants in detect_consonantal_skeleton_variants(all_names).items():
        if len(variants) > 1:
            cur = con.execute(
                "INSERT INTO skeleton_variant_groups (corpus_id, skeleton) VALUES (?,?)",
                (hur_corpus_id, skeleton),
            )
            grp_id = cur.lastrowid
            for form in variants:
                con.execute(
                    "INSERT INTO skeleton_variant_members (group_id, name_form) VALUES (?,?)",
                    (grp_id, form),
                )

    con.commit()
    print(f"  Total Hurrian names now: {len(all_names)}")
    con.close()
    print("Done.")


if __name__ == "__main__":
    expand()
