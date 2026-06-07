"""
db_setup.py — Erstellt und befüllt die SQLite-Datenbank ancient_names.db.

Schema-Prinzipien:
  - Alle Kernentitäten tragen eine language_id bzw. corpus_id → sprachübergreifend erweiterbar
  - Kassite, Vedisch, Sanskrit etc. liegen in derselben Tabellenstruktur
  - Belegstellen, Datierungen und Etymologien als eigene Tabellen (1:n bzw. m:n)
  - Corpus-Statistiken (Phoneme, Bigramme, Cluster) corpus-gebunden → vergleichbar
"""

import json
import sqlite3
import re
from collections import Counter
from pathlib import Path

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
    analyze_theophoric_productivity,
    discover_suffixes,
)

DB_PATH = "ancient_names.db"
ENRICHED_JSON = "data/kassite_names_db_enriched.json"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
-- ── Referenz-Tabellen ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS languages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    iso_code    TEXT UNIQUE,          -- z. B. "kas", "san", "skt-ved"
    name        TEXT NOT NULL,        -- "Kassitisch", "Sanskrit", "Vedisch"
    family      TEXT,                 -- "Isolat", "Indoarisch", …
    script      TEXT,                 -- "Keilschrift", "Devanagari", …
    time_period TEXT,                 -- Freitext, z. B. "ca. 1600–1150 BCE"
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS corpora (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,   -- "Kassite Personal Names", "Rigveda"
    language_id         INTEGER NOT NULL REFERENCES languages(id),
    time_period_start   INTEGER,         -- Jahr (negativ = BCE)
    time_period_end     INTEGER,
    region              TEXT,
    description         TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id       INTEGER REFERENCES corpora(id),
    short_ref       TEXT,           -- z. B. "BE 14 12"
    full_ref        TEXT,           -- vollständige Bibliographie
    source_type     TEXT,           -- "tablet", "inscription", "manuscript", …
    archive         TEXT,           -- Archiv / Fundort
    tablet_number   TEXT,
    museum_number   TEXT,
    notes           TEXT
);

-- ── Götter / Theophore Elemente ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS deities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL,
    language_id     INTEGER REFERENCES languages(id),
    deity_type      TEXT,           -- "Sonnengott", "Sturm", "unbekannt", …
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS deity_variants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deity_id    INTEGER NOT NULL REFERENCES deities(id),
    variant     TEXT NOT NULL,
    script      TEXT,
    notes       TEXT
);

-- ── Namen ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS names (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id       INTEGER NOT NULL REFERENCES corpora(id),
    transcription   TEXT NOT NULL,
    normalized_form TEXT,           -- kleingeschrieben, Sonderzeichen erhalten
    meaning         TEXT,
    gender          TEXT,           -- "m", "f", "unbekannt"
    name_type       TEXT,           -- "theophoric", "non-theophoric", "partial"
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_names_transcription ON names(transcription);
CREATE INDEX IF NOT EXISTS idx_names_corpus ON names(corpus_id);

-- Belegstellen (1 Name kann mehrfach belegt sein)
CREATE TABLE IF NOT EXISTS name_attestations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id         INTEGER NOT NULL REFERENCES names(id),
    source_id       INTEGER REFERENCES sources(id),
    date_text       TEXT,           -- Freitext, z. B. "Kassiten-Periode, ca. 1350 BCE"
    date_min_year   INTEGER,        -- –1350 = 1350 BCE
    date_max_year   INTEGER,
    date_calendar   TEXT,           -- "BCE", "CE", "regnal"
    context_notes   TEXT
);

-- ── Morphologie pro Name ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS name_morphology (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id             INTEGER NOT NULL UNIQUE REFERENCES names(id),
    morpheme_notation   TEXT,       -- Rohnotation aus DB, z. B. "Bug-aš"
    cv_structure        TEXT,       -- "CVCVCV"
    length_chars        INTEGER,
    syllable_count      INTEGER,
    consonantal_skeleton TEXT,      -- Konsonantenskelett (Vokale entfernt)
    -- split_kassite_morphemes-Ergebnis:
    morpheme_root       TEXT,
    morpheme_suffix     TEXT,
    -- Stämme nach Götternamen-Entfernung:
    isolated_stem       TEXT,
    stem_root           TEXT,       -- isolate_stems → split_stem_suffix → root
    stem_vowel_suffix   TEXT,       -- der abgetrennte Endvokal
    initial_phoneme     TEXT,
    final_phoneme       TEXT
);

-- Morphem-Bibliothek (sprachübergreifend wieder verwendbar)
CREATE TABLE IF NOT EXISTS morphemes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id     INTEGER REFERENCES languages(id),
    form            TEXT NOT NULL,
    morpheme_type   TEXT,       -- "root", "suffix", "prefix", "theophoric", "particle"
    meaning         TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_morphemes_form ON morphemes(form);
CREATE INDEX IF NOT EXISTS idx_morphemes_lang ON morphemes(language_id);

-- Welche Morpheme stecken in welchem Namen (Segmentierung)
CREATE TABLE IF NOT EXISTS name_morpheme_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id         INTEGER NOT NULL REFERENCES names(id),
    morpheme_id     INTEGER REFERENCES morphemes(id),
    position_order  INTEGER,        -- 1 = erstes Segment, 2 = zweites, …
    segment_form    TEXT NOT NULL,  -- konkrete Realisierung im Namen
    notes           TEXT
);

-- Verknüpfung: Name ↔ Gottheit
CREATE TABLE IF NOT EXISTS name_deity_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id     INTEGER NOT NULL REFERENCES names(id),
    deity_id    INTEGER NOT NULL REFERENCES deities(id),
    position    TEXT,   -- "initial", "final", "compound"
    notes       TEXT
);

-- ── Etymologie ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS etymologies (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    form                    TEXT NOT NULL,  -- die analysierte Form
    language_id             INTEGER REFERENCES languages(id),
    proposed_meaning        TEXT,
    cognate_language_id     INTEGER REFERENCES languages(id),
    cognate_form            TEXT,
    cognate_meaning         TEXT,
    confidence              TEXT,   -- "sicher", "wahrscheinlich", "möglich", "spekulativ"
    scholarly_ref           TEXT,
    notes                   TEXT
);

CREATE TABLE IF NOT EXISTS name_etymology_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id         INTEGER NOT NULL REFERENCES names(id),
    etymology_id    INTEGER NOT NULL REFERENCES etymologies(id),
    notes           TEXT
);

-- ── Sprachübergreifende Kognaten-Sets ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS cognate_sets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    label           TEXT NOT NULL,  -- z. B. "BURA-/BHURA- 'stark'"
    semantic_field  TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS cognate_members (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cognate_set_id  INTEGER NOT NULL REFERENCES cognate_sets(id),
    language_id     INTEGER NOT NULL REFERENCES languages(id),
    form            TEXT NOT NULL,
    meaning         TEXT,
    morpheme_type   TEXT,   -- "root", "name-element", …
    attestation     TEXT,   -- wo belegt
    notes           TEXT
);

-- ── Corpus-Statistiken ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS phoneme_frequencies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id       INTEGER NOT NULL REFERENCES corpora(id),
    phoneme         TEXT NOT NULL,
    phoneme_class   TEXT NOT NULL,  -- "consonant" | "vowel"
    count           INTEGER,
    percentage      REAL,
    UNIQUE(corpus_id, phoneme)
);

CREATE TABLE IF NOT EXISTS phoneme_position_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id   INTEGER NOT NULL REFERENCES corpora(id),
    phoneme     TEXT NOT NULL,
    position    TEXT NOT NULL,  -- "initial" | "medial" | "final"
    count       INTEGER,
    UNIQUE(corpus_id, phoneme, position)
);

CREATE TABLE IF NOT EXISTS bigram_frequencies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id   INTEGER NOT NULL REFERENCES corpora(id),
    bigram      TEXT NOT NULL,
    count       INTEGER,
    percentage  REAL,
    UNIQUE(corpus_id, bigram)
);

CREATE TABLE IF NOT EXISTS cluster_frequencies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id           INTEGER NOT NULL REFERENCES corpora(id),
    cluster             TEXT NOT NULL,
    cluster_class       TEXT,       -- z. B. "Liquida+Labiale"
    sonority_direction  TEXT,       -- "Absteigend" | "Aufsteigend" | "Plateau"
    count               INTEGER,
    percentage          REAL,
    UNIQUE(corpus_id, cluster)
);

CREATE TABLE IF NOT EXISTS suffix_frequencies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id       INTEGER NOT NULL REFERENCES corpora(id),
    suffix          TEXT NOT NULL,
    count           INTEGER,
    percentage      REAL,
    example_roots   TEXT,           -- JSON-Array
    UNIQUE(corpus_id, suffix)
);

-- Konsonantenskelett-Varianten (Schreibvarianten-Gruppen)
CREATE TABLE IF NOT EXISTS skeleton_variant_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id   INTEGER NOT NULL REFERENCES corpora(id),
    skeleton    TEXT NOT NULL,
    UNIQUE(corpus_id, skeleton)
);

CREATE TABLE IF NOT EXISTS skeleton_variant_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES skeleton_variant_groups(id),
    name_form   TEXT NOT NULL
);

-- Minimale Paare
CREATE TABLE IF NOT EXISTS minimal_pairs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus_id       INTEGER NOT NULL REFERENCES corpora(id),
    form_a          TEXT NOT NULL,
    form_b          TEXT NOT NULL,
    diff_position   INTEGER,        -- 1-basierte Position des Unterschieds
    phoneme_a       TEXT,
    phoneme_b       TEXT
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(name: str) -> str:
    return re.sub(r'[\s\-]', '', name.lower())


def _vowels_count(name: str) -> int:
    return len(re.findall(r'[aeiou]', name.lower()))


def _cv_structure(name: str) -> str:
    vowels = set('aeiouāēīūō')
    pattern = ''
    for ch in name.lower():
        if ch in vowels:
            pattern += 'V'
        elif ch.isalpha() or ch in 'šḫṣṭ':
            pattern += 'C'
        else:
            pattern += '0'
    return pattern


def _consonantal_skeleton(name: str) -> str:
    return re.sub(r'[aeiouāēīūō\s\-]', '', name.lower())


def _load_json(path: str) -> list:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

KASSITE_GODS = {
    "Bugaš":    ("Sturm/unbekannt", ["bugaš", "bugašu", "bugās"]),
    "Šugab":    ("unbekannt",       ["šugab", "sugab"]),
    "Šuriaš":   ("Sonnengott",      ["šuriaš", "suriaš", "shuriash"]),
    "Maruttaš": ("unbekannt",       ["maruttaš", "marutash"]),
    "Buriaš":   ("Sturmgott",       ["buriaš", "buriyaš", "burash"]),
    "Indaš":    ("unbekannt",       ["indaš", "indas"]),
    "Ḫarbe":    ("~ Enlil",         ["ḫarbe", "harbe"]),
    "Ḫala":     ("unbekannt",       ["ḫala", "hala"]),
    "Saḫ":      ("unbekannt",       ["saḫ", "sah"]),
    "Enlil":    ("Windgott (akk.)", ["enlil"]),
}


def insert_reference_data(cur):
    """Sprachliste und Korpora anlegen."""
    # Sprachen
    languages = [
        ("kas",     "Kassitisch",   "Sprachlich isoliert", "Keilschrift",   "ca. 1600–1150 BCE"),
        ("akk",     "Akkadisch",    "Semitisch",           "Keilschrift",   "ca. 2500–500 BCE"),
        ("skt",     "Sanskrit",     "Indoarisch",          "Devanagari",    "ca. 1500 BCE–heute"),
        ("skt-ved", "Vedisches Sanskrit", "Indoarisch",    "Devanagari",    "ca. 1500–500 BCE"),
        ("pi",      "Pali",         "Indoarisch",          "Verschiedene",  "ca. 500 BCE–heute"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO languages(iso_code, name, family, script, time_period) VALUES(?,?,?,?,?)",
        languages,
    )

    # Korpora
    kas_lang_id = cur.execute("SELECT id FROM languages WHERE iso_code='kas'").fetchone()[0]
    cur.execute(
        """INSERT OR IGNORE INTO corpora(name, language_id, time_period_start, time_period_end, region, description)
           VALUES(?,?,?,?,?,?)""",
        ("Kassite Personal Names", kas_lang_id, -1600, -1150,
         "Babylonia / Mesopotamia",
         "Kassitische Personennamen aus babylonischen Keilschrifttexten der Kassitenzeit"),
    )


def insert_deities(cur):
    kas_lang_id = cur.execute("SELECT id FROM languages WHERE iso_code='kas'").fetchone()[0]
    for canonical, (deity_type, variants) in KASSITE_GODS.items():
        cur.execute(
            "INSERT OR IGNORE INTO deities(canonical_name, language_id, deity_type) VALUES(?,?,?)",
            (canonical, kas_lang_id, deity_type),
        )
        deity_id = cur.execute(
            "SELECT id FROM deities WHERE canonical_name=? AND language_id=?",
            (canonical, kas_lang_id),
        ).fetchone()[0]
        for v in variants:
            cur.execute(
                "INSERT OR IGNORE INTO deity_variants(deity_id, variant) VALUES(?,?)",
                (deity_id, v),
            )


def _resolve_deity(cur, god_name: str) -> int | None:
    """Sucht deity_id über canonical_name oder variant."""
    row = cur.execute(
        "SELECT id FROM deities WHERE canonical_name=? COLLATE NOCASE", (god_name,)
    ).fetchone()
    if row:
        return row[0]
    row = cur.execute(
        """SELECT deity_id FROM deity_variants WHERE variant=? COLLATE NOCASE""",
        (god_name,),
    ).fetchone()
    return row[0] if row else None


def insert_names(cur, db: list, corpus_id: int):
    """Namen + Morphologie + Götter-Links aus dem enriched JSON."""
    for entry in db:
        transcription = entry.get("transcription", "").strip()
        if not transcription:
            continue

        gods = entry.get("detected_gods", [])
        name_type = "theophoric" if gods else "non-theophoric"
        meaning = entry.get("meaning", "") or ""

        cur.execute(
            """INSERT INTO names(corpus_id, transcription, normalized_form, meaning, name_type)
               VALUES(?,?,?,?,?)""",
            (corpus_id, transcription, _clean(transcription), meaning, name_type),
        )
        name_id = cur.lastrowid

        # Morphologie
        clean = _clean(transcription)
        isolated_stem = entry.get("isolated_stem")
        stem_root = entry.get("root")
        stem_vowel_suffix = entry.get("suffix")

        init_ph, final_ph = None, None
        if clean:
            init_ph = clean[0]
            final_ph = clean[-1]

        cur.execute(
            """INSERT OR IGNORE INTO name_morphology(
                name_id, morpheme_notation, cv_structure, length_chars, syllable_count,
                consonantal_skeleton, morpheme_root, morpheme_suffix,
                isolated_stem, stem_root, stem_vowel_suffix,
                initial_phoneme, final_phoneme
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                name_id,
                entry.get("morphemes") or None,
                entry.get("structure") or _cv_structure(transcription),
                len(clean),
                _vowels_count(clean),
                _consonantal_skeleton(transcription),
                entry.get("morpheme_root"),
                entry.get("morpheme_suffix"),
                isolated_stem,
                stem_root,
                stem_vowel_suffix,
                init_ph,
                final_ph,
            ),
        )

        # Götter-Links
        god_position_raw = entry.get("god_position", "")
        for god_name in gods:
            deity_id = _resolve_deity(cur, god_name)
            if deity_id is None:
                continue
            if "Anfang" in god_position_raw:
                pos = "initial"
            elif "Ende" in god_position_raw or "Mitte" in god_position_raw:
                pos = "final"
            else:
                pos = "compound"
            cur.execute(
                "INSERT INTO name_deity_links(name_id, deity_id, position) VALUES(?,?,?)",
                (name_id, deity_id, pos),
            )


# ---------------------------------------------------------------------------
# Corpus-level statistics
# ---------------------------------------------------------------------------

def insert_phoneme_stats(cur, corpus_id: int, transcriptions: list):
    consonants, vowels = analyze_phoneme_inventory(transcriptions)
    total_c = sum(consonants.values()) or 1
    total_v = sum(vowels.values()) or 1
    for ph, cnt in consonants.items():
        cur.execute(
            "INSERT OR REPLACE INTO phoneme_frequencies(corpus_id, phoneme, phoneme_class, count, percentage) VALUES(?,?,?,?,?)",
            (corpus_id, ph, "consonant", cnt, round(cnt / total_c * 100, 2)),
        )
    for ph, cnt in vowels.items():
        cur.execute(
            "INSERT OR REPLACE INTO phoneme_frequencies(corpus_id, phoneme, phoneme_class, count, percentage) VALUES(?,?,?,?,?)",
            (corpus_id, ph, "vowel", cnt, round(cnt / total_v * 100, 2)),
        )

    # Vokal-Position (initial / medial / final)
    v_init, v_med, v_fin = analyze_vowel_by_position(transcriptions)
    for pos_label, counter in [("initial", v_init), ("medial", v_med), ("final", v_fin)]:
        for ph, cnt in counter.items():
            cur.execute(
                "INSERT OR REPLACE INTO phoneme_position_stats(corpus_id, phoneme, position, count) VALUES(?,?,?,?)",
                (corpus_id, ph, pos_label, cnt),
            )


def insert_bigram_stats(cur, corpus_id: int, transcriptions: list):
    from src.linguistics import analyze_bigrams
    bigrams = analyze_bigrams(transcriptions)
    total = sum(bigrams.values()) or 1
    for bg, cnt in bigrams.items():
        cur.execute(
            "INSERT OR REPLACE INTO bigram_frequencies(corpus_id, bigram, count, percentage) VALUES(?,?,?,?)",
            (corpus_id, bg, cnt, round(cnt / total * 100, 2)),
        )


def insert_cluster_stats(cur, corpus_id: int, db: list):
    all_clusters = []
    for entry in db:
        root = entry.get("root") or entry.get("morpheme_root") or ""
        all_clusters.extend(get_consonant_clusters(root))

    cluster_counts = Counter(all_clusters)
    total = sum(cluster_counts.values()) or 1

    # Lautklassen-Zuordnung für 2er-Cluster
    categories = {
        'r': 'Liquida', 'l': 'Liquida',
        'n': 'Nasale', 'm': 'Nasale',
        'b': 'Labiale', 'p': 'Labiale', 'f': 'Labiale',
        'd': 'Dentale', 't': 'Dentale', 'z': 'Dentale',
        'g': 'Velare', 'k': 'Velare', 'ḫ': 'Velare', 'x': 'Velare',
        'š': 'Sibilanten', 's': 'Sibilanten',
    }
    sonority_scores = {
        'p': 1, 't': 1, 'k': 1, 'b': 1, 'd': 1, 'g': 1,
        'f': 2, 's': 2, 'š': 2, 'z': 2,
        'm': 3, 'n': 3, 'l': 4, 'r': 4,
        'a': 5, 'e': 5, 'i': 5, 'o': 5, 'u': 5,
    }

    for cluster, cnt in cluster_counts.items():
        cluster_class = None
        sonority_dir = None
        if len(cluster) == 2:
            c1, c2 = cluster[0].lower(), cluster[1].lower()
            cl1 = categories.get(c1, "Andere")
            cl2 = categories.get(c2, "Andere")
            cluster_class = f"{cl1}+{cl2}"
            s1 = sonority_scores.get(c1, 0)
            s2 = sonority_scores.get(c2, 0)
            if s1 > s2:
                sonority_dir = "Absteigend"
            elif s1 < s2:
                sonority_dir = "Aufsteigend"
            else:
                sonority_dir = "Plateau"
        cur.execute(
            "INSERT OR REPLACE INTO cluster_frequencies(corpus_id, cluster, cluster_class, sonority_direction, count, percentage) VALUES(?,?,?,?,?,?)",
            (corpus_id, cluster, cluster_class, sonority_dir, cnt, round(cnt / total * 100, 2)),
        )


def insert_suffix_stats(cur, corpus_id: int, transcriptions: list):
    endings = discover_suffixes(transcriptions)
    total = sum(endings.values()) or 1
    for suffix, cnt in endings.most_common(50):
        cur.execute(
            "INSERT OR REPLACE INTO suffix_frequencies(corpus_id, suffix, count, percentage) VALUES(?,?,?,?)",
            (corpus_id, suffix, cnt, round(cnt / total * 100, 2)),
        )


def insert_skeleton_variants(cur, corpus_id: int, transcriptions: list):
    variants = detect_consonantal_skeleton_variants(transcriptions)
    for skeleton, name_forms in variants.items():
        cur.execute(
            "INSERT OR IGNORE INTO skeleton_variant_groups(corpus_id, skeleton) VALUES(?,?)",
            (corpus_id, skeleton),
        )
        group_id = cur.execute(
            "SELECT id FROM skeleton_variant_groups WHERE corpus_id=? AND skeleton=?",
            (corpus_id, skeleton),
        ).fetchone()[0]
        for form in name_forms:
            cur.execute(
                "INSERT INTO skeleton_variant_members(group_id, name_form) VALUES(?,?)",
                (group_id, form),
            )


def insert_minimal_pairs(cur, corpus_id: int, transcriptions: list):
    pairs = find_minimal_pairs(transcriptions)
    for a, b in pairs:
        diff_pos = next(
            (i for i, (x, y) in enumerate(zip(a, b)) if x != y), None
        )
        ph_a = a[diff_pos] if diff_pos is not None else None
        ph_b = b[diff_pos] if diff_pos is not None else None
        cur.execute(
            "INSERT INTO minimal_pairs(corpus_id, form_a, form_b, diff_position, phoneme_a, phoneme_b) VALUES(?,?,?,?,?,?)",
            (corpus_id, a, b, (diff_pos + 1) if diff_pos is not None else None, ph_a, ph_b),
        )


# ---------------------------------------------------------------------------
# Main build routine
# ---------------------------------------------------------------------------

def build_database():
    db_path = Path(DB_PATH)
    if db_path.exists():
        db_path.unlink()
        print(f"[INFO] Vorhandene {DB_PATH} gelöscht.")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    print("[1/6] Schema erstellen …")
    cur.executescript(SCHEMA)
    con.commit()

    print("[2/6] Referenzdaten (Sprachen, Korpora) einfügen …")
    insert_reference_data(cur)
    con.commit()

    print("[3/6] Götter-Tabelle befüllen …")
    insert_deities(cur)
    con.commit()

    print("[4/6] Namen aus JSON laden …")
    db = _load_json(ENRICHED_JSON)
    corpus_id = cur.execute(
        "SELECT id FROM corpora WHERE name='Kassite Personal Names'"
    ).fetchone()[0]
    insert_names(cur, db, corpus_id)
    con.commit()
    name_count = cur.execute("SELECT COUNT(*) FROM names").fetchone()[0]
    print(f"         {name_count} Namen eingefügt.")

    print("[5/6] Corpus-Statistiken berechnen und einfügen …")
    transcriptions = [e.get("transcription", "") for e in db if e.get("transcription")]
    insert_phoneme_stats(cur, corpus_id, transcriptions)
    insert_bigram_stats(cur, corpus_id, transcriptions)
    insert_cluster_stats(cur, corpus_id, db)
    insert_suffix_stats(cur, corpus_id, transcriptions)
    insert_skeleton_variants(cur, corpus_id, transcriptions)
    insert_minimal_pairs(cur, corpus_id, transcriptions)
    con.commit()

    print("[6/6] Indizes und Abschluss …")
    con.execute("ANALYZE")
    con.commit()
    con.close()

    size_kb = db_path.stat().st_size // 1024
    print(f"\n[OK] {DB_PATH} erfolgreich erstellt ({size_kb} KB).")
    print("     Tabellen: languages, corpora, sources, deities, deity_variants,")
    print("               names, name_attestations, name_morphology,")
    print("               morphemes, name_morpheme_segments, name_deity_links,")
    print("               etymologies, name_etymology_links,")
    print("               cognate_sets, cognate_members,")
    print("               phoneme_frequencies, phoneme_position_stats,")
    print("               bigram_frequencies, cluster_frequencies,")
    print("               suffix_frequencies, skeleton_variant_groups,")
    print("               skeleton_variant_members, minimal_pairs")


if __name__ == "__main__":
    build_database()
