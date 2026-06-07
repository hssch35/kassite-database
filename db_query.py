"""
db_query.py — Hilfsfunktionen für Abfragen, Einfügen und sprachübergreifende
               Vergleiche auf ancient_names.db.

Verwendung:
    from db_query import open_db, get_names_by_deity, cross_language_morpheme_search
    con = open_db()
    rows = get_names_by_deity(con, "Saḫ")
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = "ancient_names.db"


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------

def open_db(path: str = DB_PATH) -> sqlite3.Connection:
    """Öffnet die Datenbank mit aktivierten Foreign Keys."""
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row   # Spalten-Zugriff per Name
    return con


# ---------------------------------------------------------------------------
# Einfüge-Helfer
# ---------------------------------------------------------------------------

def add_language(con: sqlite3.Connection, iso_code: str, name: str,
                 family: str = None, script: str = None,
                 time_period: str = None, notes: str = None) -> int:
    """
    Fügt eine neue Sprache ein (oder gibt die id der vorhandenen zurück).

    Beispiel:
        lang_id = add_language(con, "ta", "Tamil", "Dravidisch", "Brahmischrift")
    """
    cur = con.cursor()
    cur.execute(
        """INSERT INTO languages(iso_code, name, family, script, time_period, notes)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(iso_code) DO UPDATE SET name=excluded.name""",
        (iso_code, name, family, script, time_period, notes),
    )
    con.commit()
    return cur.execute("SELECT id FROM languages WHERE iso_code=?", (iso_code,)).fetchone()[0]


def add_corpus(con: sqlite3.Connection, name: str, language_iso: str,
               time_period_start: int = None, time_period_end: int = None,
               region: str = None, description: str = None) -> int:
    """
    Fügt ein Korpus für eine Sprache ein.

    Beispiel:
        cid = add_corpus(con, "Rigveda", "skt-ved", -1500, -900, "Indien")
    """
    cur = con.cursor()
    lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code=?", (language_iso,)
    ).fetchone()
    if not lang_id:
        raise ValueError(f"Sprache mit iso_code='{language_iso}' nicht gefunden.")
    lang_id = lang_id[0]
    cur.execute(
        """INSERT INTO corpora(name, language_id, time_period_start, time_period_end, region, description)
           VALUES(?,?,?,?,?,?)""",
        (name, lang_id, time_period_start, time_period_end, region, description),
    )
    con.commit()
    return cur.lastrowid


def add_name(con: sqlite3.Connection, corpus_id: int, transcription: str,
             meaning: str = None, name_type: str = None, notes: str = None) -> int:
    """
    Fügt einen Namen in ein Korpus ein.

    Beispiel:
        nid = add_name(con, cid, "Indra", "Donnergott", "theophoric")
    """
    import re
    normalized = re.sub(r'[\s\-]', '', transcription.lower())
    cur = con.cursor()
    cur.execute(
        """INSERT INTO names(corpus_id, transcription, normalized_form, meaning, name_type, notes)
           VALUES(?,?,?,?,?,?)""",
        (corpus_id, transcription, normalized, meaning, name_type, notes),
    )
    con.commit()
    return cur.lastrowid


def add_etymology(con: sqlite3.Connection, form: str, language_iso: str,
                  proposed_meaning: str = None,
                  cognate_language_iso: str = None, cognate_form: str = None,
                  cognate_meaning: str = None, confidence: str = "möglich",
                  scholarly_ref: str = None, notes: str = None) -> int:
    """
    Legt einen etymologischen Eintrag an.

    Beispiel:
        eid = add_etymology(con, "bura", "kas", "stark/Held",
                            cognate_language_iso="skt-ved", cognate_form="bala",
                            cognate_meaning="Kraft", confidence="möglich",
                            scholarly_ref="Balkan 1954")
    """
    cur = con.cursor()
    lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code=?", (language_iso,)
    ).fetchone()
    if not lang_id:
        raise ValueError(f"Sprache '{language_iso}' nicht gefunden.")
    lang_id = lang_id[0]

    cog_lang_id = None
    if cognate_language_iso:
        row = cur.execute(
            "SELECT id FROM languages WHERE iso_code=?", (cognate_language_iso,)
        ).fetchone()
        cog_lang_id = row[0] if row else None

    cur.execute(
        """INSERT INTO etymologies(form, language_id, proposed_meaning,
               cognate_language_id, cognate_form, cognate_meaning,
               confidence, scholarly_ref, notes)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (form, lang_id, proposed_meaning, cog_lang_id, cognate_form,
         cognate_meaning, confidence, scholarly_ref, notes),
    )
    con.commit()
    return cur.lastrowid


def link_name_etymology(con: sqlite3.Connection, name_id: int,
                        etymology_id: int, notes: str = None):
    """Verknüpft einen Namen mit einem etymologischen Eintrag."""
    con.execute(
        "INSERT INTO name_etymology_links(name_id, etymology_id, notes) VALUES(?,?,?)",
        (name_id, etymology_id, notes),
    )
    con.commit()


def add_cognate_set(con: sqlite3.Connection, label: str,
                    semantic_field: str = None, notes: str = None) -> int:
    """Legt ein sprachübergreifendes Kognaten-Set an."""
    cur = con.cursor()
    cur.execute(
        "INSERT INTO cognate_sets(label, semantic_field, notes) VALUES(?,?,?)",
        (label, semantic_field, notes),
    )
    con.commit()
    return cur.lastrowid


def add_cognate_member(con: sqlite3.Connection, cognate_set_id: int,
                       language_iso: str, form: str, meaning: str = None,
                       morpheme_type: str = None, attestation: str = None,
                       notes: str = None):
    """Fügt ein Element zu einem Kognaten-Set hinzu."""
    cur = con.cursor()
    lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code=?", (language_iso,)
    ).fetchone()
    if not lang_id:
        raise ValueError(f"Sprache '{language_iso}' nicht gefunden.")
    cur.execute(
        """INSERT INTO cognate_members(cognate_set_id, language_id, form, meaning,
               morpheme_type, attestation, notes)
           VALUES(?,?,?,?,?,?,?)""",
        (cognate_set_id, lang_id[0], form, meaning, morpheme_type, attestation, notes),
    )
    con.commit()


def add_attestation(con: sqlite3.Connection, name_id: int,
                    date_text: str = None, date_min_year: int = None,
                    date_max_year: int = None, date_calendar: str = "BCE",
                    source_id: int = None, context_notes: str = None):
    """Fügt eine Belegstelle für einen Namen ein."""
    con.execute(
        """INSERT INTO name_attestations(name_id, source_id, date_text,
               date_min_year, date_max_year, date_calendar, context_notes)
           VALUES(?,?,?,?,?,?,?)""",
        (name_id, source_id, date_text, date_min_year, date_max_year,
         date_calendar, context_notes),
    )
    con.commit()


# ---------------------------------------------------------------------------
# Abfrage-Funktionen
# ---------------------------------------------------------------------------

def get_names_by_deity(con: sqlite3.Connection, deity_name: str) -> list[sqlite3.Row]:
    """
    Alle Namen, die ein bestimmtes theophores Element enthalten.

    Beispiel:
        rows = get_names_by_deity(con, "Saḫ")
        for r in rows: print(r['transcription'], r['position'])
    """
    return con.execute(
        """SELECT n.transcription, n.meaning, ndl.position,
                  d.canonical_name AS deity, l.name AS language, c.name AS corpus
           FROM name_deity_links ndl
           JOIN names n ON n.id = ndl.name_id
           JOIN deities d ON d.id = ndl.deity_id
           JOIN corpora c ON c.id = n.corpus_id
           JOIN languages l ON l.id = c.language_id
           WHERE d.canonical_name = ? COLLATE NOCASE
              OR d.canonical_name IN (
                  SELECT deity_id FROM deity_variants WHERE variant=? COLLATE NOCASE
              )
           ORDER BY n.transcription""",
        (deity_name, deity_name),
    ).fetchall()


def get_name_details(con: sqlite3.Connection, transcription: str) -> dict:
    """
    Vollständige Detailansicht eines Namens (Morphologie + Götter + Etymologie).

    Beispiel:
        details = get_name_details(con, "Burna-Buriaš")
    """
    row = con.execute(
        "SELECT * FROM names WHERE transcription=? COLLATE NOCASE LIMIT 1",
        (transcription,),
    ).fetchone()
    if not row:
        return {}

    name_id = row["id"]
    morphology = con.execute(
        "SELECT * FROM name_morphology WHERE name_id=?", (name_id,)
    ).fetchone()
    deities = con.execute(
        """SELECT d.canonical_name, ndl.position
           FROM name_deity_links ndl JOIN deities d ON d.id=ndl.deity_id
           WHERE ndl.name_id=?""",
        (name_id,),
    ).fetchall()
    etymologies = con.execute(
        """SELECT e.form, e.proposed_meaning, l.name AS language,
                  e.cognate_form, cl.name AS cognate_language,
                  e.confidence, e.scholarly_ref
           FROM name_etymology_links nel
           JOIN etymologies e ON e.id=nel.etymology_id
           LEFT JOIN languages l ON l.id=e.language_id
           LEFT JOIN languages cl ON cl.id=e.cognate_language_id
           WHERE nel.name_id=?""",
        (name_id,),
    ).fetchall()
    attestations = con.execute(
        "SELECT * FROM name_attestations WHERE name_id=?", (name_id,)
    ).fetchall()

    return {
        "name":        dict(row),
        "morphology":  dict(morphology) if morphology else {},
        "deities":     [dict(d) for d in deities],
        "etymologies": [dict(e) for e in etymologies],
        "attestations": [dict(a) for a in attestations],
    }


def search_names(con: sqlite3.Connection, pattern: str,
                 language_iso: str = None) -> list[sqlite3.Row]:
    """
    Volltext-Suche über Transkription (SQL LIKE).
    Optional: auf eine Sprache einschränken.

    Beispiel:
        rows = search_names(con, "%buriaš%", language_iso="kas")
    """
    if language_iso:
        return con.execute(
            """SELECT n.transcription, n.meaning, n.name_type,
                      l.name AS language, c.name AS corpus
               FROM names n
               JOIN corpora c ON c.id=n.corpus_id
               JOIN languages l ON l.id=c.language_id
               WHERE n.transcription LIKE ? AND l.iso_code=?
               ORDER BY n.transcription""",
            (pattern, language_iso),
        ).fetchall()
    return con.execute(
        """SELECT n.transcription, n.meaning, n.name_type,
                  l.name AS language, c.name AS corpus
           FROM names n
           JOIN corpora c ON c.id=n.corpus_id
           JOIN languages l ON l.id=c.language_id
           WHERE n.transcription LIKE ?
           ORDER BY n.transcription""",
        (pattern,),
    ).fetchall()


def get_names_by_suffix(con: sqlite3.Connection, suffix: str,
                        language_iso: str = None) -> list[sqlite3.Row]:
    """
    Alle Namen mit einem bestimmten morphologischen Suffix.

    Beispiel:
        rows = get_names_by_suffix(con, "aš", language_iso="kas")
    """
    q = """SELECT n.transcription, nm.morpheme_root, nm.morpheme_suffix,
                  l.name AS language
           FROM names n
           JOIN name_morphology nm ON nm.name_id=n.id
           JOIN corpora c ON c.id=n.corpus_id
           JOIN languages l ON l.id=c.language_id
           WHERE nm.morpheme_suffix=?"""
    params: list = [suffix]
    if language_iso:
        q += " AND l.iso_code=?"
        params.append(language_iso)
    q += " ORDER BY n.transcription"
    return con.execute(q, params).fetchall()


def get_names_by_skeleton(con: sqlite3.Connection, skeleton: str) -> list[sqlite3.Row]:
    """
    Alle Namen mit einem bestimmten Konsonantenskelett (Schreibvarianten-Gruppen).

    Beispiel:
        rows = get_names_by_skeleton(con, "šbl")
    """
    return con.execute(
        """SELECT svm.name_form, l.name AS language, c.name AS corpus
           FROM skeleton_variant_members svm
           JOIN skeleton_variant_groups svg ON svg.id=svm.group_id
           JOIN corpora c ON c.id=svg.corpus_id
           JOIN languages l ON l.id=c.language_id
           WHERE svg.skeleton=?""",
        (skeleton,),
    ).fetchall()


def get_phoneme_stats(con: sqlite3.Connection, corpus_name: str,
                      phoneme_class: str = None) -> list[sqlite3.Row]:
    """
    Phonem-Häufigkeiten für ein Korpus.

    Beispiel:
        rows = get_phoneme_stats(con, "Kassite Personal Names", phoneme_class="vowel")
    """
    q = """SELECT pf.phoneme, pf.phoneme_class, pf.count, pf.percentage
           FROM phoneme_frequencies pf
           JOIN corpora c ON c.id=pf.corpus_id
           WHERE c.name=?"""
    params: list = [corpus_name]
    if phoneme_class:
        q += " AND pf.phoneme_class=?"
        params.append(phoneme_class)
    q += " ORDER BY pf.count DESC"
    return con.execute(q, params).fetchall()


def get_top_bigrams(con: sqlite3.Connection, corpus_name: str,
                    limit: int = 15) -> list[sqlite3.Row]:
    """
    Top-N Bigramme eines Korpus.

    Beispiel:
        rows = get_top_bigrams(con, "Kassite Personal Names", limit=10)
    """
    return con.execute(
        """SELECT bf.bigram, bf.count, bf.percentage
           FROM bigram_frequencies bf
           JOIN corpora c ON c.id=bf.corpus_id
           WHERE c.name=?
           ORDER BY bf.count DESC LIMIT ?""",
        (corpus_name, limit),
    ).fetchall()


def get_theophoric_productivity(con: sqlite3.Connection,
                                corpus_name: str = None) -> list[sqlite3.Row]:
    """
    Für jede Gottheit: Anzahl einzigartiger Stämme, mit denen sie kombiniert wird.

    Beispiel:
        rows = get_theophoric_productivity(con, "Kassite Personal Names")
    """
    q = """SELECT d.canonical_name AS deity,
                  COUNT(DISTINCT nm.isolated_stem) AS unique_stems,
                  COUNT(DISTINCT ndl.name_id) AS total_names,
                  l.name AS language
           FROM name_deity_links ndl
           JOIN deities d ON d.id=ndl.deity_id
           JOIN names n ON n.id=ndl.name_id
           LEFT JOIN name_morphology nm ON nm.name_id=n.id
           JOIN corpora c ON c.id=n.corpus_id
           JOIN languages l ON l.id=c.language_id"""
    params: list = []
    if corpus_name:
        q += " WHERE c.name=?"
        params.append(corpus_name)
    q += " GROUP BY d.id ORDER BY total_names DESC"
    return con.execute(q, params).fetchall()


def get_minimal_pairs(con: sqlite3.Connection, corpus_name: str) -> list[sqlite3.Row]:
    """
    Minimale Paare (Hamming-Distanz 1) eines Korpus.

    Beispiel:
        rows = get_minimal_pairs(con, "Kassite Personal Names")
    """
    return con.execute(
        """SELECT mp.form_a, mp.form_b, mp.diff_position, mp.phoneme_a, mp.phoneme_b
           FROM minimal_pairs mp
           JOIN corpora c ON c.id=mp.corpus_id
           WHERE c.name=?
           ORDER BY mp.diff_position""",
        (corpus_name,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Sprachübergreifende Vergleichs-Abfragen
# ---------------------------------------------------------------------------

def cross_language_morpheme_search(con: sqlite3.Connection,
                                   form: str) -> list[sqlite3.Row]:
    """
    Sucht eine Morphem-Form über alle Sprachen hinweg — in Namen (morpheme_root /
    morpheme_suffix), in der Etymologie-Tabelle und in cognate_members.

    Beispiel:
        rows = cross_language_morpheme_search(con, "bur")
        # → kassitische Namen mit Wurzel 'bur', vedische Kognaten, Etymologie-Einträge
    """
    pattern = f"%{form}%"
    # Namen
    names_hits = con.execute(
        """SELECT 'name' AS source_table,
                  n.transcription AS form, n.meaning,
                  l.name AS language, c.name AS corpus,
                  nm.morpheme_root, nm.morpheme_suffix
           FROM names n
           JOIN name_morphology nm ON nm.name_id=n.id
           JOIN corpora c ON c.id=n.corpus_id
           JOIN languages l ON l.id=c.language_id
           WHERE nm.morpheme_root LIKE ? OR nm.morpheme_suffix LIKE ?
                 OR nm.isolated_stem LIKE ?""",
        (pattern, pattern, pattern),
    ).fetchall()
    # Kognaten
    cognate_hits = con.execute(
        """SELECT 'cognate' AS source_table,
                  cm.form, cm.meaning,
                  l.name AS language, cs.label AS corpus,
                  cm.morpheme_type AS morpheme_root, '' AS morpheme_suffix
           FROM cognate_members cm
           JOIN languages l ON l.id=cm.language_id
           JOIN cognate_sets cs ON cs.id=cm.cognate_set_id
           WHERE cm.form LIKE ?""",
        (pattern,),
    ).fetchall()
    # Etymologien
    etym_hits = con.execute(
        """SELECT 'etymology' AS source_table,
                  e.form, e.proposed_meaning AS meaning,
                  l.name AS language, '' AS corpus,
                  e.cognate_form AS morpheme_root, e.confidence AS morpheme_suffix
           FROM etymologies e
           JOIN languages l ON l.id=e.language_id
           WHERE e.form LIKE ? OR e.cognate_form LIKE ?""",
        (pattern, pattern),
    ).fetchall()
    return list(names_hits) + list(cognate_hits) + list(etym_hits)


def compare_phoneme_inventories(con: sqlite3.Connection,
                                corpus_a: str,
                                corpus_b: str) -> dict:
    """
    Vergleicht die Phonem-Inventare zweier Korpora.
    Gibt Dict mit 'only_in_a', 'only_in_b', 'shared' zurück.

    Beispiel:
        diff = compare_phoneme_inventories(con, "Kassite Personal Names", "Rigveda")
    """
    def get_phonemes(corpus: str) -> set:
        rows = con.execute(
            """SELECT pf.phoneme FROM phoneme_frequencies pf
               JOIN corpora c ON c.id=pf.corpus_id WHERE c.name=?""",
            (corpus,),
        ).fetchall()
        return {r["phoneme"] for r in rows}

    a = get_phonemes(corpus_a)
    b = get_phonemes(corpus_b)
    return {
        "only_in_a": sorted(a - b),
        "only_in_b": sorted(b - a),
        "shared":    sorted(a & b),
    }


def find_cognate_sets_for_name(con: sqlite3.Connection,
                               transcription: str) -> list[sqlite3.Row]:
    """
    Alle Kognaten-Sets, die eine Morphem-Form aus dem gesuchten Namen enthalten.

    Beispiel:
        rows = find_cognate_sets_for_name(con, "Burna-Buriaš")
    """
    row = con.execute(
        "SELECT id FROM names WHERE transcription=? COLLATE NOCASE LIMIT 1",
        (transcription,),
    ).fetchone()
    if not row:
        return []
    name_id = row["id"]
    # Morphem-Form aus Morphologie holen
    morph = con.execute(
        "SELECT morpheme_root, isolated_stem FROM name_morphology WHERE name_id=?",
        (name_id,),
    ).fetchone()
    if not morph:
        return []
    search_forms = [f for f in [morph["morpheme_root"], morph["isolated_stem"]] if f]
    results = []
    for form in search_forms:
        pattern = f"%{form.lower()}%"
        hits = con.execute(
            """SELECT cs.label, cm.form, cm.meaning, l.name AS language
               FROM cognate_members cm
               JOIN cognate_sets cs ON cs.id=cm.cognate_set_id
               JOIN languages l ON l.id=cm.language_id
               WHERE LOWER(cm.form) LIKE ?""",
            (pattern,),
        ).fetchall()
        results.extend(hits)
    return results


def get_corpus_summary(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """
    Überblick über alle Korpora: Sprache, Zeitraum, Namenszahl.

    Beispiel:
        for row in get_corpus_summary(con): print(dict(row))
    """
    return con.execute(
        """SELECT c.name AS corpus, l.name AS language, l.iso_code,
                  c.time_period_start, c.time_period_end, c.region,
                  COUNT(n.id) AS name_count
           FROM corpora c
           JOIN languages l ON l.id=c.language_id
           LEFT JOIN names n ON n.corpus_id=c.id
           GROUP BY c.id
           ORDER BY c.time_period_start""",
    ).fetchall()


def get_names_by_initial_phoneme(con: sqlite3.Connection, phoneme: str,
                                 language_iso: str = None) -> list[sqlite3.Row]:
    """
    Alle Namen mit einem bestimmten Anlaut.

    Beispiel:
        rows = get_names_by_initial_phoneme(con, "š", language_iso="kas")
    """
    q = """SELECT n.transcription, nm.initial_phoneme, l.name AS language
           FROM names n
           JOIN name_morphology nm ON nm.name_id=n.id
           JOIN corpora c ON c.id=n.corpus_id
           JOIN languages l ON l.id=c.language_id
           WHERE nm.initial_phoneme=?"""
    params: list = [phoneme]
    if language_iso:
        q += " AND l.iso_code=?"
        params.append(language_iso)
    return con.execute(q, params).fetchall()


def get_skeleton_variant_groups(con: sqlite3.Connection,
                                corpus_name: str,
                                min_members: int = 2) -> list[dict]:
    """
    Gibt alle Konsonantenskelett-Gruppen mit ihren Mitgliedern zurück.

    Beispiel:
        groups = get_skeleton_variant_groups(con, "Kassite Personal Names")
        for g in groups: print(g['skeleton'], g['members'])
    """
    groups = con.execute(
        """SELECT svg.id, svg.skeleton
           FROM skeleton_variant_groups svg
           JOIN corpora c ON c.id=svg.corpus_id
           WHERE c.name=?""",
        (corpus_name,),
    ).fetchall()
    result = []
    for g in groups:
        members = con.execute(
            "SELECT name_form FROM skeleton_variant_members WHERE group_id=?",
            (g["id"],),
        ).fetchall()
        if len(members) >= min_members:
            result.append({
                "skeleton": g["skeleton"],
                "members":  [m["name_form"] for m in members],
            })
    return sorted(result, key=lambda x: -len(x["members"]))


# ---------------------------------------------------------------------------
# Schnellübersicht (CLI-Nutzung)
# ---------------------------------------------------------------------------

def print_summary(con: sqlite3.Connection):
    """Druckt eine kompakte Übersicht der Datenbank."""
    print("=== ancient_names.db — Überblick ===\n")
    for row in get_corpus_summary(con):
        start = row["time_period_start"]
        end   = row["time_period_end"]
        period = ""
        if start and end:
            def fmt(y):
                return f"{abs(y)} BCE" if y < 0 else f"{y} CE"
            period = f"ca. {fmt(start)}–{fmt(end)}"
        print(f"  Korpus:  {row['corpus']}")
        print(f"  Sprache: {row['language']} ({row['iso_code']})")
        print(f"  Zeitraum:{period or '—'}")
        print(f"  Namen:   {row['name_count']}")
        print()

    print("--- Sprachen ---")
    for row in con.execute("SELECT iso_code, name, family FROM languages ORDER BY name"):
        print(f"  [{row['iso_code']}] {row['name']} ({row['family'] or '—'})")

    print("\n--- Götter (Kassite) ---")
    for row in con.execute(
        "SELECT canonical_name, deity_type FROM deities ORDER BY canonical_name"
    ):
        print(f"  {row['canonical_name']} — {row['deity_type'] or '?'}")

    print("\n--- Tabellen-Zeilenzahlen ---")
    tables = [
        "languages", "corpora", "sources", "deities", "deity_variants",
        "names", "name_attestations", "name_morphology",
        "morphemes", "name_morpheme_segments", "name_deity_links",
        "etymologies", "name_etymology_links",
        "cognate_sets", "cognate_members",
        "phoneme_frequencies", "phoneme_position_stats",
        "bigram_frequencies", "cluster_frequencies",
        "suffix_frequencies", "skeleton_variant_groups",
        "skeleton_variant_members", "minimal_pairs",
    ]
    for t in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<35} {count:>6} Zeilen")


if __name__ == "__main__":
    if not Path(DB_PATH).exists():
        print(f"[ERROR] {DB_PATH} nicht gefunden. Bitte zuerst db_setup.py ausführen.")
    else:
        con = open_db()
        print_summary(con)
        con.close()
