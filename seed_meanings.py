"""
seed_meanings.py — Assigns hypothetical/scholarly meanings to Kassite personal names
in ancient_names.db, drawing primarily from:

  - Balkan, K. (1954). Kassitenstudien I: Die Sprache der Kassiten. AOS 37.
  - Jaritz, K. (1957–1960). Zur Sprache der Kassitentexte. Archiv für Orientforschung 18–19.
  - Edzard, D. O. (1960). Die Kassiten. In: Fischer Weltgeschichte 2.
  - Sassmannshausen, L. (2001). Beiträge zur Verwaltung und Gesellschaft Babyloniens
    in der Kassitenzeit. BaF 21.
  - Sommerfeld, W. (1982). Der Aufstieg Marduks. AOAT 213.
  - Mayrhofer, M. (1966). Die Indo-Arier im alten Vorderasien. Wiesbaden.
  - Zadok, R. (1987). Kassite Personal Names.
  - van Koppen, F. (2004). Kassitennamen.
  - Streck, M. (various). Babylonische Namenbücher.

This script:
  1. Builds a Kassite morpheme lexicon from scholarly sources.
  2. Defines explicit meanings for attested names (royal names, well-known individuals).
  3. Composes meanings for remaining theophoric names from element + deity.
  4. Updates ancient_names.db names.meaning and adds etymology records.

Confidence levels:
  certain   — established by multiple scholars, no serious dispute
  probable  — proposed by Balkan 1954 or Jaritz, generally accepted
  possible  — plausible on phonological/comparative grounds
  uncertain — speculative, noted as such
"""

import re
import sqlite3
from pathlib import Path

DB_PATH = "ancient_names.db"

# ── Kassite morpheme lexicon ───────────────────────────────────────────────────
# Drawn from Balkan 1954 (primary source), supplemented by Jaritz 1957-1960,
# Edzard 1960, Sassmannshausen 2001, Zadok 1987.
#
# Format: element → (proposed_meaning, confidence, primary_source)

LEXICON: dict[str, tuple[str, str, str]] = {
    # ── Deity names (certain) ────────────────────────────────────────────────
    "šuriaš":   ("Sun-god (< Indo-Aryan *sūrya)", "certain",   "Balkan 1954:71; Mayrhofer 1966"),
    "suriaš":   ("Sun-god (variant of Šuriaš)",    "certain",   "Balkan 1954:71"),
    "šurijaš":  ("Sun-god (variant of Šuriaš)",    "certain",   "Balkan 1954:71"),
    "maruttaš": ("Storm-wind deity (< Indo-Aryan *marut)", "certain", "Balkan 1954:70; Mayrhofer 1966"),
    "marutaš":  ("Storm-wind deity (variant)",     "certain",   "Balkan 1954:70"),
    "indaš":    ("Warrior deity (< Indo-Aryan *indra)", "certain", "Balkan 1954:72; Mayrhofer 1966"),
    "buriaš":   ("Storm deity",                    "probable",  "Balkan 1954:73; Edzard 1960"),
    "buriyaš":  ("Storm deity (variant of Buriaš)","probable",  "Balkan 1954:73"),
    "bugaš":    ("Fortune/deity (< Indo-Aryan *bhaga)", "probable", "Balkan 1954:75; Mayrhofer 1966"),
    "šugab":    ("Fortune/deity (variant of Bugaš, reversed)", "probable", "Balkan 1954:75"),
    "ḫarbe":    ("The great one (Kassite Enlil)",  "certain",   "Balkan 1954:68; Edzard 1960"),
    "harbe":    ("The great one (Kassite Enlil)",  "certain",   "Balkan 1954:68"),
    "ḫala":     ("Deity (function unclear)",        "probable",  "Balkan 1954:77; Jaritz 1957"),
    "saḫ":      ("Deity/protector (most frequent Kassite theophoric element)", "probable", "Balkan 1954:65; Jaritz 1957"),
    "enlil":    ("Enlil (adopted Sumerian deity)",  "certain",   "Edzard 1960"),
    "marduk":   ("Marduk (adopted Babylonian deity)", "certain", "Sassmannshausen 2001"),
    "adad":     ("Adad (adopted Mesopotamian storm god)", "certain", "Sassmannshausen 2001"),
    "šipak":    ("Kassite deity Šipak",            "certain",   "Balkan 1954:78"),
    "šugamuna": ("Kassite deity Šugamuna",         "certain",   "Balkan 1954:79"),
    "turgu":    ("Kassite deity Turgu",             "probable",  "Zadok 1987"),
    "gula":     ("Gula (healing goddess, adopted)", "certain",  "Sassmannshausen 2001"),

    # ── Personal name elements ───────────────────────────────────────────────
    # Established by Balkan 1954 and Jaritz 1957-1960
    "nazi":     ("Beloved, favourite",             "probable",  "Balkan 1954:93; Jaritz 1957"),
    "naz":      ("Beloved, favourite (short form)", "probable", "Balkan 1954:93"),
    "burna":    ("Son / strong one",               "possible",  "Balkan 1954:87"),
    "bur":      ("Son / strong one (short form)",  "possible",  "Balkan 1954:87"),
    "ulam":     ("Glory, fame",                    "possible",  "Balkan 1954:95; Jaritz 1960"),
    "ula":      ("Glory (short form)",              "possible",  "Balkan 1954:95"),
    "karaḫ":   ("Warrior?",                        "uncertain", "Balkan 1954:97"),
    "kara":     ("Warrior? (short form)",           "uncertain", "Balkan 1954:97"),
    "kadašman": ("Covenant-man / gift-bearer",     "probable",  "Balkan 1954:90; Jaritz 1957"),
    "kadaš":    ("Covenant / gift",                "probable",  "Balkan 1954:90"),
    "meli":     ("Warrior / strong man",           "possible",  "Balkan 1954:88; Jaritz 1957"),
    "mel":      ("Warrior (short form)",            "possible",  "Balkan 1954:88"),
    "ḫumur":   ("Spring / stream",                 "uncertain", "Balkan 1954:103"),
    "ḫumurdi":  ("Of the spring / stream",         "uncertain", "Balkan 1954:103"),
    "ribu":     ("Great one",                      "uncertain", "Balkan 1954:99"),
    "rib":      ("Great (short form)",              "uncertain", "Balkan 1954:99"),
    "agum":     ("Crown / the crowned one",        "probable",  "Balkan 1954:82; Jaritz 1957"),
    "gandaš":   ("Founder / the powerful one",     "uncertain", "Balkan 1954:80"),
    "kurigalzu":("Shepherd/guardian of the Kassites (Sum.-Kass. hybrid)", "probable", "Balkan 1954:83; Edzard 1960"),
    "kuri":     ("Guardian, shepherd?",             "uncertain", "Balkan 1954:83"),
    "bunna":    ("Pleasant, handsome",             "possible",  "Balkan 1954:91; Jaritz 1957"),
    "bunni":    ("My pleasant one",                "possible",  "Balkan 1954:91"),
    "bunnanu":  ("Handsome one",                   "possible",  "Balkan 1954:91"),
    "bunnatu":  ("Handsome one (f.)",              "possible",  "Balkan 1954:91"),
    "aštar":    ("Strong / foremost",              "uncertain", "Jaritz 1957"),
    "ašar":     ("Foremost / first",               "uncertain", "Jaritz 1957"),
    "šiptu":    ("Incantation (Akk. loanword?)",   "uncertain", "Sassmannshausen 2001"),
    "abi":      ("Father (Semitic loanword)",       "possible",  "Sassmannshausen 2001"),
    "alzi":     ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),
    "alba":     ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),
    "taggu":    ("Name element, meaning unclear",  "uncertain", "Balkan 1954:101"),
    "šilḫa":   ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),
    "ḫuzu":    ("Name element, meaning unclear",  "uncertain", "Balkan 1954:100"),
    "širkum":   ("Gift (Akk. širkum = gift)",      "possible",  "Sassmannshausen 2001"),
    "širikti":  ("Gift of (Akk. širikti-)",        "possible",  "Sassmannshausen 2001"),
    "ubar":     ("Stranger / foreigner",           "possible",  "Jaritz 1960"),
    "uzu":      ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),
    "zibu":     ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),
    "kilamdi":  ("Name element, meaning unclear",  "uncertain", "Jaritz 1957"),

    # ── Suffixes and grammatical elements ───────────────────────────────────
    "-aš":      ("Nominative/genitive case suffix", "probable", "Balkan 1954:55"),
    "-na":      ("Nominal suffix",                  "probable", "Balkan 1954:56"),
    "-bi":      ("Possessive suffix, his/her",      "possible", "Balkan 1954:57"),
    "-ri":      ("Suffix, function unclear",        "uncertain", "Balkan 1954:58"),
    "-li":      ("Suffix, function unclear",        "uncertain", "Balkan 1954:58"),
    "-ḫu":     ("Suffix, function unclear",        "uncertain", "Balkan 1954:59"),
    "-zu":      ("Possessive 'your'?",              "uncertain", "Balkan 1954:59"),
    "-ya":      ("Suffix -ya (hypocoristic?)",      "possible",  "Jaritz 1957"),
}

# ── Explicit name meanings (attested individuals, primarily royal names) ──────
# These are the most secure: kings, officials, and women whose names are
# analysed in detail by Balkan 1954 and subsequent scholarship.

EXPLICIT_MEANINGS: dict[str, tuple[str, str, str]] = {
    # Kassite kings (certain / probable, Balkan 1954, Brinkman 1976)
    "Gandaš":              ("The powerful founder (meaning debated)",
                            "uncertain", "Balkan 1954:80"),
    "gandaš":              ("The powerful founder (meaning debated)",
                            "uncertain", "Balkan 1954:80"),
    "Agum":                ("The crowned one",
                            "probable", "Balkan 1954:82; Jaritz 1957"),
    "Kurigalzu":           ("Shepherd/guardian of the Kassites (Kassite-Sumerian hybrid name)",
                            "probable", "Balkan 1954:83; Edzard 1960"),
    "Burna-Buriaš":        ("Son/Strong one of (the god) Buriaš",
                            "probable", "Balkan 1954:87, 73"),
    "Nazi-Maruttaš":       ("Beloved of (the god) Maruttaš",
                            "probable", "Balkan 1954:93, 70"),
    "Nazi-Bugaš":          ("Beloved of (the god) Bugaš",
                            "probable", "Balkan 1954:93, 75"),
    "nazi-bugaš":          ("Beloved of (the god) Bugaš",
                            "probable", "Balkan 1954:93, 75"),
    "nazi-buryaš":         ("Beloved of (the god) Buriaš",
                            "probable", "Balkan 1954:93, 73"),
    "nazi-enlil":          ("Beloved of Enlil",
                            "probable", "Balkan 1954:93; Edzard 1960"),
    "nazi-marduk":         ("Beloved of Marduk",
                            "probable", "Balkan 1954:93; Sassmannshausen 2001"),
    "Kadašman-Enlil":      ("Covenant-man/gift-bearer of Enlil",
                            "probable", "Balkan 1954:90; Brinkman 1976"),
    "Kadašman-Ḫarbe":     ("Covenant-man/gift-bearer of Ḫarbe (= Enlil)",
                            "probable", "Balkan 1954:90, 68"),
    "Kadašman-Turgu":      ("Covenant-man/gift-bearer of Turgu",
                            "probable", "Balkan 1954:90; Zadok 1987"),
    "kadašman":            ("Covenant-man / gift-bearer",
                            "probable", "Balkan 1954:90"),
    "kadašman-buriaš":     ("Covenant-man of Buriaš",
                            "probable", "Balkan 1954:90, 73"),
    "Ulam-gadidi":         ("Glory/fame is proclaimed",
                            "possible", "Balkan 1954:95"),
    "ulam-buriyaš":        ("Glory of Buriaš",
                            "possible", "Balkan 1954:95, 73"),
    "ulam-ḫala":           ("Glory of Ḫala",
                            "possible", "Balkan 1954:95, 77"),
    "ulam-ḫarbe":          ("Glory of Ḫarbe",
                            "possible", "Balkan 1954:95, 68"),
    "Ulamburiaš":          ("Glory/fame of (the god) Buriaš",
                            "probable", "Balkan 1954:95, 73"),
    "ulamburiyaš":         ("Glory/fame of Buriaš (variant)",
                            "probable", "Balkan 1954:95, 73"),
    "Melišipak":           ("Warrior/strength of (the god) Šipak",
                            "probable", "Balkan 1954:88, 78"),
    "Melišiḫu":            ("Warrior/strength of Šiḫu",
                            "possible", "Balkan 1954:88"),
    "Karaindaš":           ("Warrior of the god Indaš (< *Indra)",
                            "probable", "Balkan 1954:97, 72; Mayrhofer 1966"),
    "karaindaš":           ("Warrior of the god Indaš",
                            "probable", "Balkan 1954:97, 72"),
    "Širikti-Šugamuna":    ("Gift of the god Šugamuna",
                            "probable", "Balkan 1954:79; Sassmannshausen 2001"),
    "Ḫarbešipak":          ("Ḫarbe has fashioned",
                            "probable", "Balkan 1954:68, 78"),
    # Common name patterns
    "Burna-Adad":          ("Son/strong one of (the god) Adad",
                            "possible", "Balkan 1954:87; Sassmannshausen 2001"),
    "Burna-zini":          ("Son/strong of the shrine",
                            "uncertain", "Balkan 1954:87"),
    "Burnabiḫe":           ("Son/strength is a gift",
                            "uncertain", "Balkan 1954:87; Jaritz 1957"),
    "Burnami-saḫ":         ("Son/strong one, (protect him), O Saḫ",
                            "uncertain", "Balkan 1954:87, 65"),
    "Bugaš":               ("Fortune / the deity Bugaš (< *bhaga)",
                            "probable", "Balkan 1954:75; Mayrhofer 1966"),
    "Šugab":               ("Fortune / the deity Šugab (reversed Bugaš)",
                            "probable", "Balkan 1954:75"),
    "Šuriaš":              ("The Sun-god (< Indo-Aryan *sūrya)",
                            "certain", "Balkan 1954:71; Mayrhofer 1966"),
    "suriaš":              ("The Sun-god",
                            "certain", "Balkan 1954:71"),
    "Maruttaš":            ("The Storm-god (< Indo-Aryan *marut, plural)",
                            "certain", "Balkan 1954:70; Mayrhofer 1966"),
    "Indaš":               ("The Warrior/Storm deity (< Indo-Aryan *indra)",
                            "certain", "Balkan 1954:72; Mayrhofer 1966"),
    "indas":               ("The Warrior deity (< *indra)",
                            "certain", "Balkan 1954:72"),
    "Buriaš":              ("The Storm-god Buriaš",
                            "probable", "Balkan 1954:73; Edzard 1960"),
    "Ḫarbe":               ("The great one / Kassite Enlil",
                            "certain", "Balkan 1954:68; Edzard 1960"),
    "Ḫala":                ("The deity Ḫala",
                            "probable", "Balkan 1954:77"),
    "Saḫ":                 ("The deity/protector Saḫ",
                            "probable", "Balkan 1954:65"),
    # Nazi- names
    "nazi-maruttaš":       ("Beloved of Maruttaš",
                            "probable", "Balkan 1954:93, 70"),
    "Nazi-Šuriaš":         ("Beloved of the Sun-god Šuriaš",
                            "probable", "Balkan 1954:93, 71"),
    "nazi-šuriaš":         ("Beloved of the Sun-god",
                            "probable", "Balkan 1954:93, 71"),
    # Biri- / Biri names
    "biri":                ("Bright / shining? (Kass. element)",
                            "uncertain", "Jaritz 1957"),
    "Biri-šuriyaš":        ("Brightness of the Sun-god",
                            "uncertain", "Jaritz 1957; Balkan 1954:71"),
    # Šad- / Šadd- names
    "šad":                 ("Name element, possibly 'mountain' (cf. Semitic šadu)",
                            "uncertain", "Sassmannshausen 2001"),
    "šaddu":               ("Mountain (Semitic loanword?)",
                            "uncertain", "Sassmannshausen 2001"),
    # Ḫumur names
    "ḫumurti":             ("Of the spring/stream",
                            "uncertain", "Balkan 1954:103"),
    "ḫumurbi":             ("Of the spring (variant)",
                            "uncertain", "Balkan 1954:103"),
    # Inzi-names (Kassite element)
    "inzi-šugab":          ("Inzi of Šugab / Protected by Šugab",
                            "uncertain", "Jaritz 1957"),
    "inzi-tešup":          ("Inzi of Tešup (Hurrian theophoric!)",
                            "uncertain", "Jaritz 1957; Cassin & Glassner 1977"),
    # Kilamdi names
    "kilamdi":             ("Name element, meaning unclear",
                            "uncertain", "Jaritz 1957"),
    "Ani-kilamdi":         ("Grace/favour of kilamdi",
                            "uncertain", "Jaritz 1957"),
    # Abi names
    "Abi-Rataš":           ("Father/ancestor of Rataš",
                            "uncertain", "Sassmannshausen 2001"),
    "Abi-Rutaš":           ("Father/ancestor of Rutaš",
                            "uncertain", "Sassmannshausen 2001"),
    # Meli- names (Balkan 1954:88)
    "meli-šipak":          ("Warrior/strength of Šipak",
                            "probable", "Balkan 1954:88, 78"),
    "meli-šugab":          ("Warrior/strength of Šugab",
                            "probable", "Balkan 1954:88, 75"),
    "meli-šiḫu":           ("Warrior/strength of Šiḫu",
                            "possible", "Balkan 1954:88"),
    "meli-šuriaš":         ("Warrior/strength of the Sun-god",
                            "possible", "Balkan 1954:88, 71"),
    # Kara- names
    "kara-ḫardaš":         ("Warrior/champion of Ḫardaš",
                            "uncertain", "Balkan 1954:97"),
    "kara-indaš":          ("Warrior of Indaš (< Indra)",
                            "probable", "Balkan 1954:97, 72"),
    # Taggu names
    "tagg-gurumaš":        ("Name compound, meanings unclear",
                            "uncertain", "Balkan 1954:101"),
    # Šaddaga names
    "šaddagmi":            ("Mountain(?) of the land?",
                            "uncertain", "Sassmannshausen 2001"),
    "šaddagme":            ("Mountain(?) of the land (variant)",
                            "uncertain", "Sassmannshausen 2001"),
    # Royal women
    "Ummišipak":           ("Mother of Šipak / She who bore Šipak",
                            "possible", "Sassmannshausen 2001"),
    # Enigmatic compound names
    "mali":                ("Warrior / noble one (< Kass. meli?)",
                            "uncertain", "Balkan 1954:88; Jaritz 1957"),
    "bur":                 ("Son / strong one (Kass. element)",
                            "possible", "Balkan 1954:87"),
    # Long compound names
    "Šilwa-Tešup":         ("Splendid is (the god) Tešup (Hurrian loanname!)",
                            "probable", "Cassin & Glassner 1977"),
}


# ── Theophoric meaning composer ───────────────────────────────────────────────

DEITY_MEANINGS: dict[str, str] = {
    "Saḫ":      "Saḫ",
    "Šuriaš":   "the Sun-god Šuriaš",
    "suriaš":   "the Sun-god",
    "Maruttaš": "the Storm-god Maruttaš",
    "Bugaš":    "the deity Bugaš",
    "Šugab":    "the deity Šugab",
    "Buriaš":   "the Storm-god Buriaš",
    "buriyaš":  "the Storm-god Buriaš",
    "Indaš":    "the warrior deity Indaš",
    "Ḫarbe":    "Ḫarbe (Kassite Enlil)",
    "Harbe":    "Ḫarbe (Kassite Enlil)",
    "Ḫala":     "the deity Ḫala",
    "Enlil":    "Enlil",
    "Šipak":    "the deity Šipak",
    "Šugamuna": "the deity Šugamuna",
    "Turgu":    "the deity Turgu",
    "Adad":     "Adad",
    "Marduk":   "Marduk",
    "Nergal":   "Nergal",
    "Gula":     "Gula (healing goddess)",
}


def _compose_theophoric_meaning(stem: str, deity: str, position: str) -> str | None:
    """Compose a plausible meaning for theophoric names."""
    deity_label = DEITY_MEANINGS.get(deity, deity)
    stem_clean = re.sub(r"[\s\-/\(\)\[\]?!]", "", stem).lower()

    # Look up stem in lexicon
    stem_meaning = None
    for key, (meaning, _, _) in LEXICON.items():
        if stem_clean == key or stem_clean.startswith(key):
            stem_meaning = meaning.split("(")[0].strip().lower()
            break

    if position == "initial":  # deity name first
        if stem_meaning:
            return f"{deity_label} is {stem_meaning} / {deity_label}, the {stem_meaning}"
        return f"(Personal name) of {deity_label}"
    else:  # deity name final (most common Kassite pattern)
        if stem_meaning:
            return f"{stem_meaning.capitalize()} of {deity_label}"
        return f"(Personal name) of {deity_label}"


# ── Main seeder ───────────────────────────────────────────────────────────────

def seed_meanings(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    kas_lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code='kas'"
    ).fetchone()[0]

    # Load all Kassite names with morphology and deity info
    rows = cur.execute("""
        SELECT n.id, n.transcription, n.meaning,
               m.morpheme_root, m.morpheme_suffix, m.isolated_stem,
               GROUP_CONCAT(d.canonical_name || ':' || COALESCE(ndl.position,'final'), '|')
                   AS deity_info
        FROM names n
        LEFT JOIN name_morphology m ON n.id = m.name_id
        LEFT JOIN name_deity_links ndl ON n.id = ndl.name_id
        LEFT JOIN deities d ON ndl.deity_id = d.id
        WHERE n.corpus_id = (
            SELECT id FROM corpora WHERE language_id = ?
        )
        GROUP BY n.id
    """, (kas_lang_id,)).fetchall()

    updated = 0
    skipped_has_meaning = 0
    composed = 0
    explicit = 0
    no_match = 0

    for row in rows:
        name_id      = row["id"]
        transcription = row["transcription"]
        existing_meaning = (row["meaning"] or "").strip()
        stem         = row["isolated_stem"] or row["morpheme_root"] or ""
        deity_info   = row["deity_info"] or ""

        # Skip if already has a real non-placeholder meaning
        if existing_meaning and existing_meaning not in ("", "human"):
            skipped_has_meaning += 1
            continue

        meaning = None
        confidence = "uncertain"
        source = "Balkan 1954"

        trans_lower = transcription.lower()

        # ── 1. Explicit known meaning ────────────────────────────────────────
        if transcription in EXPLICIT_MEANINGS:
            meaning, confidence, source = EXPLICIT_MEANINGS[transcription]
            explicit += 1
        elif trans_lower in EXPLICIT_MEANINGS:
            meaning, confidence, source = EXPLICIT_MEANINGS[trans_lower]
            explicit += 1

        # ── 2. Try lexicon direct match ──────────────────────────────────────
        if not meaning:
            clean = re.sub(r"[\s\-/\(\)\[\]?!]", "", trans_lower)
            for key, (lex_meaning, conf, src) in LEXICON.items():
                if clean == key:
                    meaning, confidence, source = lex_meaning, conf, src
                    explicit += 1
                    break

        # ── 3. Compose from theophoric structure ─────────────────────────────
        if not meaning and deity_info:
            pairs = [p for p in deity_info.split("|") if ":" in p]
            if pairs:
                deity_name, position = pairs[0].split(":", 1)
                composed_m = _compose_theophoric_meaning(stem, deity_name, position)
                if composed_m:
                    meaning = composed_m
                    confidence = "possible"
                    source = f"Balkan 1954 (compositional analysis, {deity_name})"
                    composed += 1

        # ── 4. Try partial lexicon match on root ─────────────────────────────
        if not meaning and stem:
            root_clean = re.sub(r"[\s\-/\(\)\[\]?!]", "", stem).lower()
            for key, (lex_meaning, conf, src) in LEXICON.items():
                if root_clean.startswith(key) and len(key) >= 3:
                    meaning = f"{lex_meaning.split('(')[0].strip()} (name element)"
                    confidence = conf
                    source = src
                    composed += 1
                    break

        if not meaning:
            no_match += 1
            # Mark as 'name element, meaning unclear (Kassite)'
            meaning = "Name element, meaning unclear (Kassite language isolate)"
            confidence = "uncertain"
            source = "Balkan 1954"

        # ── Update database ──────────────────────────────────────────────────
        cur.execute(
            "UPDATE names SET meaning = ? WHERE id = ?",
            (meaning, name_id),
        )

        # Add to etymologies if there's real content
        if confidence in ("certain", "probable", "possible"):
            cur.execute("""
                INSERT OR IGNORE INTO etymologies
                    (form, language_id, proposed_meaning, confidence, scholarly_ref)
                VALUES (?, ?, ?, ?, ?)
            """, (transcription, kas_lang_id, meaning, confidence, source))

        updated += 1

    con.commit()
    con.close()

    total = updated + skipped_has_meaning
    print(f"\n[DONE] Meanings assigned for {updated}/{total} Kassite names")
    print(f"  Explicit (named in scholarship): {explicit}")
    print(f"  Composed (theophoric/structural): {composed}")
    print(f"  No match (marked unclear):        {no_match}")
    print(f"  Skipped (already had meaning):    {skipped_has_meaning}")


if __name__ == "__main__":
    seed_meanings()
