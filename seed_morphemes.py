"""
seed_morphemes.py

Populates the `morphemes` and `name_morpheme_segments` tables in ancient_names.db
with Kassite morpheme data from Balkan 1954 "Kassitenstudien I" and related sources.

Strategy:
  1. Insert known roots, suffixes and theophoric elements into `morphemes`.
  2. For each Kassite name, attempt segmentation (root + suffix + theophoric prefix/suffix)
     and record each segment in `name_morpheme_segments`.
"""

import re
import sqlite3
from pathlib import Path

DB_PATH = "ancient_names.db"

# ---------------------------------------------------------------------------
# Morpheme library (Balkan 1954, Brinkman 1976, Sassmannshausen 2001)
# ---------------------------------------------------------------------------

# (form, morpheme_type, meaning, notes)
MORPHEMES: list[tuple[str, str, str, str]] = [
    # ── Roots ─────────────────────────────────────────────────────────────
    ("Burna",   "root", "son / strong",            "Balkan 1954:87"),
    ("Nazi",    "root", "beloved / gracious",       "Balkan 1954:93"),
    ("Kuri",    "root", "shepherd / guardian",      "Balkan 1954:83"),
    ("Agum",    "root", "flood / wave",             "Balkan 1954:75"),
    ("Šipta",   "root", "gift",                     "Balkan 1954:97"),
    ("Meli",    "root", "beloved",                  "Balkan 1954:89"),
    ("Abi",     "root", "my father",                "Balkan 1954:75 (Semitic loanword)"),
    ("Abi",     "root", "my father",                "Balkan 1954:75"),
    ("Rataš",   "root", "lord / warrior",           "Balkan 1954:95"),
    ("Rutaš",   "root", "lord / warrior",           "Balkan 1954:95 (variant)"),
    ("Karaḫ",   "root", "young man / warrior",      "Balkan 1954:82"),
    ("Kadaš",   "root", "sacred / holy",            "Balkan 1954:82"),
    ("Galzu",   "root", "of the Kassites",          "Balkan 1954:83; Sumerian loanword"),
    ("Šuqamuna","root", "the god Šuqamuna",         "Balkan 1954:98"),
    ("Ḫarbe",   "root", "the god Ḫarbe (≈ Enlil)", "Balkan 1954:79"),
    ("Ḫala",    "root", "the god Ḫala",             "Balkan 1954:79"),
    ("Ḫarbé",   "root", "the god Ḫarbe",            "Balkan 1954:79 (variant)"),
    ("Šipa",    "root", "shepherd / gift",           "Balkan 1954:97"),
    ("Ulam",    "root", "strong / powerful",         "Balkan 1954:101"),
    ("Kaššu",   "root", "Kassite (ethnonym root)",  "Balkan 1954:82"),
    ("Gula",    "root", "great / the goddess Gula", "Balkan 1954 (Sumerian loanword)"),
    ("Bēl",     "root", "lord (Akkadian)",           "Akkadian loanword"),
    ("Išbi",    "root", "he is great",               "Balkan 1954:81 (Semitic)"),
    ("Dadi",    "root", "beloved / darling",         "Balkan 1954:77"),
    ("Laba",    "root", "lion (Semitic?)",            "Balkan 1954:85"),
    ("Tibu",    "root", "good / strong",              "Balkan 1954:99"),
    ("Aḫu",     "root", "brother (Semitic)",          "Akkadian aḫu"),
    ("Kudu",    "root", "clan / kin",                 "Balkan 1954:83"),
    ("Šagarakti","root","protection of / arm of",     "Balkan 1954:96 (theophoric compound)"),
    ("Mubal",   "root", "strong / exalted",           "Balkan 1954:91"),
    ("Enlil",   "root", "the god Enlil (Sumerian)",  "Sumerian loanword"),
    ("Marduk",  "root", "the god Marduk",             "Akkadian"),
    ("Šamaš",   "root", "the god Šamaš / sun",        "Akkadian/Sumerian"),
    ("Adad",    "root", "the storm god Adad",          "Akkadian"),
    ("Ninurta", "root", "the god Ninurta",             "Sumerian"),
    ("Nana",    "root", "the goddess Nana/Inanna",     "Sumerian"),
    ("Sin",     "root", "the moon god Sin",             "Akkadian"),
    ("Iddina",  "root", "he gave (Akkadian)",           "Akkadian iddin + a"),

    # ── Kassite deity roots ────────────────────────────────────────────────
    ("Šuriaš",  "theophoric", "the sun god (< Indo-Aryan *Sūrya)",  "Balkan 1954:98; Mayrhofer 1966"),
    ("Maruttaš","theophoric", "storm deity (< Indo-Aryan *Marut)",   "Balkan 1954:88; Mayrhofer 1966"),
    ("Buriaš",  "theophoric", "storm god (~ Vedic *Vāyu?)",          "Balkan 1954:74"),
    ("Indaš",   "theophoric", "warrior god (< Indo-Aryan *Indra)",   "Balkan 1954:72; Mayrhofer 1966"),
    ("Šugab",   "theophoric", "the god Šugab",                        "Balkan 1954:98"),
    ("Bugaš",   "theophoric", "the god Bugaš",                        "Balkan 1954:74"),
    ("Saḫ",     "theophoric", "the god Saḫ",                          "Balkan 1954:96"),
    ("Šuqamuna","theophoric", "the god Šuqamuna",                      "Balkan 1954:98"),
    ("Šimaḫ",   "theophoric", "the god Šimaḫ",                         "Balkan 1954:97"),
    ("Ḫarbe",   "theophoric", "the god Ḫarbe (≈ Enlil)",               "Balkan 1954:79"),
    ("Ḫala",    "theophoric", "the god Ḫala",                           "Balkan 1954:79"),

    # ── Suffixes ──────────────────────────────────────────────────────────
    ("aš",    "suffix", "nominal / adjectival suffix",         "Balkan 1954:105"),
    ("iaš",   "suffix", "genitive / adjectival suffix",        "Balkan 1954:105"),
    ("ak",    "suffix", "agentive / possessive suffix",         "Balkan 1954:103"),
    ("ikku",  "suffix", "nominal suffix",                       "Balkan 1954:104"),
    ("itta",  "suffix", "nominal suffix (< *-ita)",             "Balkan 1954:104"),
    ("atta",  "suffix", "paternal suffix / -ite",               "Balkan 1954:103"),
    ("uḫu",   "suffix", "nominal suffix",                       "Balkan 1954:104"),
    ("ina",   "suffix", "locative suffix (Akkadian influence)", "Balkan 1954:104"),
    ("šu",    "suffix", "pronominal suffix (his)",              "Balkan 1954:105"),
    ("i",     "suffix", "genitive / short form suffix",         "Balkan 1954:103"),
    ("a",     "suffix", "nominative / vocative suffix",         "Balkan 1954:103"),
    ("u",     "suffix", "nominative suffix (Akkadian pattern)", "Balkan 1954:103"),
    ("zi",    "suffix", "short life / vitality morpheme",       "Sassmannshausen 2001"),
    ("dun",   "suffix", "gift / given",                         "Balkan 1954:104"),
    ("kašir", "suffix", "complete / whole",                     "Balkan 1954:104"),
]

# ---------------------------------------------------------------------------
# Known Kassite theophoric elements for segmentation
# ---------------------------------------------------------------------------

THEOPHORIC_ELEMENTS = [
    "Šuriaš", "Maruttaš", "Buriaš", "Indaš", "Šugab", "Bugaš",
    "Saḫ", "Šuqamuna", "Šimaḫ", "Ḫarbe", "Ḫala", "Ḫarbé",
    "Enlil", "Marduk", "Šamaš", "Adad", "Ninurta", "Sin", "Nana", "Gula",
]

SUFFIXES_RANKED = [
    "iaš", "aš", "ikku", "itta", "atta", "uḫu", "ina", "šu",
    "ak", "zi", "dun", "kašir", "i", "a", "u",
]

# ---------------------------------------------------------------------------
# Segmentation helpers
# ---------------------------------------------------------------------------

def _clean(name: str) -> str:
    return re.sub(r"[\s\-]", "", name)


def segment_name(name: str) -> list[tuple[str, str]]:
    """
    Returns a list of (segment_form, morpheme_type) tuples.
    Types: 'theophoric', 'root', 'suffix', 'unknown'
    """
    clean = _clean(name)
    segments: list[tuple[str, str]] = []

    # 1. Check for theophoric components (prefix or suffix position)
    theophoric_found: list[tuple[str, str]] = []  # (form, position)
    remaining = clean

    for deity in sorted(THEOPHORIC_ELEMENTS, key=len, reverse=True):
        d_low = deity.lower()
        r_low = remaining.lower()
        if r_low.startswith(d_low) and len(remaining) > len(deity):
            theophoric_found.append((deity, "prefix"))
            remaining = remaining[len(deity):]
            break
        elif r_low.endswith(d_low) and len(remaining) > len(deity):
            theophoric_found.append((deity, "suffix"))
            remaining = remaining[:-len(deity)]
            break

    # 2. Strip suffix from remaining
    suffix_found = None
    for suf in sorted(SUFFIXES_RANKED, key=len, reverse=True):
        if remaining.lower().endswith(suf.lower()) and len(remaining) > len(suf) + 1:
            suffix_found = suf
            remaining = remaining[:-len(suf)]
            break

    # 3. Build segment list
    # Prefix theophoric comes first
    for deity, pos in theophoric_found:
        if pos == "prefix":
            segments.append((deity, "theophoric"))

    # Root (whatever remains)
    if remaining:
        segments.append((remaining, "root"))

    # Suffix
    if suffix_found:
        segments.append((suffix_found, "suffix"))

    # Suffix theophoric comes last
    for deity, pos in theophoric_found:
        if pos == "suffix":
            segments.append((deity, "theophoric"))

    return segments if segments else [(clean, "unknown")]


# ---------------------------------------------------------------------------
# Main seeding function
# ---------------------------------------------------------------------------

def seed(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    # Get Kassite language id
    kas_lang_id = con.execute(
        "SELECT id FROM languages WHERE iso_code = 'kas'"
    ).fetchone()[0]

    # Get Kassite corpus id
    kas_corpus_id = con.execute(
        "SELECT id FROM corpora WHERE language_id = ?", (kas_lang_id,)
    ).fetchone()[0]

    # ── 1. Insert morphemes ────────────────────────────────────────────────
    print("Inserting morphemes …")
    seen_forms: set[str] = set()
    form_to_id: dict[str, int] = {}

    # Clear existing morphemes for Kassite to avoid duplication
    con.execute("DELETE FROM name_morpheme_segments")
    con.execute("DELETE FROM morphemes WHERE language_id = ?", (kas_lang_id,))

    for form, mtype, meaning, notes in MORPHEMES:
        key = (form.lower(), mtype)
        if key in seen_forms:
            continue
        seen_forms.add(key)
        cur = con.execute(
            "INSERT INTO morphemes (language_id, form, morpheme_type, meaning, notes) VALUES (?,?,?,?,?)",
            (kas_lang_id, form, mtype, meaning, notes),
        )
        form_to_id[key] = cur.lastrowid

    print(f"  Inserted {len(form_to_id)} morphemes.")

    # Build lookup: form_lower → morpheme_id (prefer longest match)
    morph_lookup: dict[tuple[str, str], int] = form_to_id

    # ── 2. Segment all Kassite names ─────────────────────────────────────
    print("Segmenting Kassite names …")
    names = con.execute(
        "SELECT id, transcription FROM names WHERE corpus_id = ?", (kas_corpus_id,)
    ).fetchall()

    total_segments = 0
    for name_id, transcription in names:
        segs = segment_name(transcription)
        for order, (form, mtype) in enumerate(segs):
            # Try to find matching morpheme_id
            key = (form.lower(), mtype)
            morph_id = morph_lookup.get(key)
            if morph_id is None:
                # Try root fallback (any matching form regardless of type)
                for (k_form, k_type), mid in morph_lookup.items():
                    if k_form == form.lower():
                        morph_id = mid
                        break

            con.execute(
                """INSERT INTO name_morpheme_segments
                   (name_id, morpheme_id, position_order, segment_form, notes)
                   VALUES (?,?,?,?,?)""",
                (name_id, morph_id, order, form, mtype),
            )
            total_segments += 1

    con.commit()
    print(f"  Segmented {len(names)} names → {total_segments} total segments.")

    # ── 3. Report ─────────────────────────────────────────────────────────
    theo_count = con.execute(
        "SELECT COUNT(DISTINCT name_id) FROM name_morpheme_segments WHERE notes = 'theophoric'"
    ).fetchone()[0]
    suffix_count = con.execute(
        "SELECT COUNT(DISTINCT name_id) FROM name_morpheme_segments WHERE notes = 'suffix'"
    ).fetchone()[0]
    print(f"  Names with theophoric segment: {theo_count}")
    print(f"  Names with suffix segment:     {suffix_count}")

    # Top segments
    print("\nTop 15 root segments:")
    for row in con.execute("""
        SELECT segment_form, COUNT(*) c FROM name_morpheme_segments
        WHERE notes = 'root' GROUP BY segment_form ORDER BY c DESC LIMIT 15
    """).fetchall():
        print(f"  {row[0]:<20} {row[1]}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    seed()
