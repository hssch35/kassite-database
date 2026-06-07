"""
seed_corpora.py — Loads Hurrian (Nuzi) and Sanskrit/Vedic name corpora
into ancient_names.db alongside the existing Kassite corpus.

Sources:
  Hurrian: Cassin & Glassner (1977) "Anthroponymes et Anthroponymie Nuziens";
           Gelb (1943) "Hurrians and Subarians"; CDLI Nuzi archive.
  Sanskrit/Vedic: Rigveda (RV), Atharvaveda (AV), Mahābhārata (MBh);
                  Mayrhofer "Etymologisches Wörterbuch des Altindoarischen".
"""

import sqlite3
import json
import re
from pathlib import Path
from collections import Counter

from src.linguistics import (
    analyze_phoneme_inventory,
    analyze_bigrams,
    detect_consonantal_skeleton_variants,
    find_minimal_pairs,
    discover_suffixes,
    get_consonant_clusters,
    analyze_cluster_types,
    analyze_sonority_slope,
    analyze_syllable_distribution,
    analyze_vowel_by_position,
    analyze_positions,
)

DB_PATH = "ancient_names.db"

# ── Hurrian corpus ────────────────────────────────────────────────────────────
# Personal names primarily from the Nuzi archive (ca. 1500–1350 BCE, Arrapha/Kirkuk)
# Theophoric elements: Tešup (storm), Šauška (Ištar), Ḫebat (solar), Kumarbi,
#                      Šimige (sun), Nabarwe, Nergal (adopted Mesopotamian)

HURRIAN_DEITIES = [
    # (canonical_name, deity_type, notes)
    ("Tešup",    "storm",    "Chief storm deity of the Hurrian pantheon"),
    ("Šauška",   "love/war", "Hurrian equivalent of Ištar; also storm aspects"),
    ("Ḫebat",    "sun",      "Solar goddess, consort of Tešup"),
    ("Kumarbi",  "earth",    "Father of gods, grain deity; cognate to Enlil?"),
    ("Šimige",   "sun",      "Sun god of the Hurrian pantheon"),
    ("Nabarwe",  "deity",    "Hurrian deity, appears in Nuzi names"),
    ("Nergal",   "death",    "Mesopotamian deity adopted into Hurrian pantheon"),
    ("Ḫumba",    "deity",    "Elamite-influenced deity; appears in Hurrian names"),
    ("Tilla",    "deity",    "Bull deity / divine title in Hurrian onomastics"),
]

# Format: (transcription, meaning_or_None, name_type, notes)
HURRIAN_NAMES = [
    # Tešup theophoric (storm god)
    ("Muš-Tešup",     "Tešup is strong",         "theophoric", "Nuzi archive"),
    ("Ar-Tešup",      "Tešup gave",               "theophoric", "Nuzi archive"),
    ("Šilwa-Tešup",   "Tešup is splendid",        "theophoric", "Nuzi; also Tell Brak"),
    ("Atal-Tešup",    "Tešup is mighty",          "theophoric", "Nuzi archive"),
    ("Kušši-Tešup",   "Tešup is firm",            "theophoric", "Nuzi archive"),
    ("Ḫumpa-Tešup",   "Tešup of Ḫumpa",          "theophoric", "Nuzi archive"),
    ("Šenni-Tešup",   "Tešup is the lord",        "theophoric", "Nuzi archive"),
    ("Pula-ḫali",     None,                       "theophoric", "Tešup context; Nuzi"),
    ("Tauka-Tešup",   None,                       "theophoric", "Nuzi archive"),
    ("Akaw-Atil",     None,                       "personal",   "Nuzi archive"),
    # Tilla (bull deity) theophoric
    ("Ḫašip-Tilla",   "Tilla has granted",        "theophoric", "Very frequent Nuzi name"),
    ("Šurḫi-Tilla",   "Tilla is exalted",         "theophoric", "Nuzi archive"),
    ("Pal-Tilla",      "Tilla-face",              "theophoric", "Nuzi archive"),
    ("Nai-Tilla",     "Tilla is my lord",         "theophoric", "Nuzi archive"),
    ("Unap-Tae",      None,                       "theophoric", "Nuzi archive"),
    ("Enna-mati",     "Lord of the land",         "theophoric", "Nuzi; enna = lord"),
    # Šauška theophoric
    ("Ar-Šauška",     "Šauška gave",              "theophoric", "Nuzi archive"),
    ("Šauš-atal",     "Šauška is mighty",         "theophoric", "Nuzi archive"),
    # Personal / descriptive names
    ("Tarmiya",       "Swift",                    "personal",   "Very common Hurrian name"),
    ("Šeḫliya",       None,                       "personal",   "Nuzi archive"),
    ("Ḫutiya",        None,                       "personal",   "Nuzi archive"),
    ("Wantiya",       None,                       "personal",   "Nuzi archive"),
    ("Zinni-ya",      None,                       "personal",   "Nuzi archive; -ya suffix"),
    ("Tulpun-naya",   "Splendid one",             "personal",   "Nuzi; talpun = splendid"),
    ("Ipša-ḫalu",     None,                       "personal",   "Nuzi; compare Kassite ipšaḫalu"),
    ("Ḫanaya",        "My grace / favour",        "personal",   "Nuzi; ḫane = grace"),
    ("Kušši-ḫarpe",  None,                       "personal",   "Nuzi archive"),
    ("Enna-ya",       "He is lord",               "personal",   "Nuzi; enna = lord"),
    ("Šekar-ru",      None,                       "personal",   "Nuzi archive"),
    ("Ḫašiya",        None,                       "personal",   "Nuzi archive"),
    ("Purna-ya",      None,                       "personal",   "Nuzi; purni = house"),
    ("Tarmi-ya",      "Swift",                    "personal",   "Variant of Tarmiya"),
    ("Zilip-tilla",   None,                       "theophoric", "Nuzi; zilip = ?"),
    ("Nūr-kubi",      "Light of Kubi",            "hybrid",     "Akkadian-Hurrian hybrid"),
    ("Kirip-šarri",   "Devoted to the king",      "personal",   "Hybrid name; Nuzi"),
    ("Akap-šenni",    "The lord has seized",      "theophoric", "Nuzi"),
    ("Šurki-Tilla",   None,                       "theophoric", "Nuzi archive"),
    ("Ḫumpa-zah",    None,                       "personal",   "Nuzi archive"),
    ("Ippi-ya",       None,                       "personal",   "Nuzi archive"),
    ("Nabu-šarru",    "Nabu is king",             "hybrid",     "Akkadian-Hurrian hybrid name"),
    ("Uantia",        None,                       "personal",   "Variant of Wantiya"),
    ("Keliya",        None,                       "personal",   "Nuzi; notable diplomat"),
    ("Šukriya",       None,                       "personal",   "Nuzi archive"),
    ("Atanah-ili",    None,                       "hybrid",     "Nuzi, hybrid with Semitic"),
    ("Ḫurpiya",       None,                       "personal",   "Nuzi archive"),
    ("Šeḫal-Tešup",  None,                       "theophoric", "Nuzi archive"),
    ("Itḫi-Tešup",   "Tešup is with me",         "theophoric", "Mitanni royal context"),
    ("Artašumara",    None,                       "royal",      "Mitanni prince name"),
    ("Tušratta",      "Furious chariot",          "royal",      "Mitanni king; ca. 1370 BCE"),
    ("Šattarna",      None,                       "royal",      "Mitanni king"),
    ("Parsatatar",    None,                       "royal",      "Mitanni king"),
    ("Šauštatar",     None,                       "royal",      "Mitanni king"),
    ("Artaššumara",   None,                       "royal",      "Mitanni context"),
    ("Kiri-ya",       None,                       "personal",   "Nuzi archive"),
    ("Ḫašuar",        None,                       "personal",   "Possible cognate with Kassite name"),
    ("Taḫar-Tešup",  None,                       "theophoric", "Nuzi archive"),
    ("Mušap-Tešup",  None,                       "theophoric", "Nuzi archive"),
]

# ── Sanskrit / Vedic corpus ───────────────────────────────────────────────────
# Personal names from Rigveda (RV), Atharvaveda (AV), Epics, and Vedic literature.
# Key theophoric elements: Indra, Mitra, Varuṇa, Agni, Sūrya, Marut, Soma, Vāyu

SANSKRIT_DEITIES = [
    # (canonical_name, deity_type, notes)
    ("Indra",    "storm/warrior", "Chief warrior deity; cognate with Kassite Indaš?"),
    ("Mitra",    "covenant",      "Solar covenant deity; also in Mitanni theophoric names"),
    ("Varuṇa",  "cosmic order",  "God of cosmic order (ṛta); Vedic sky deity"),
    ("Agni",     "fire",          "Fire deity, central in Vedic ritual"),
    ("Sūrya",   "sun",           "Sun deity; cognate with Kassite Šuriaš?"),
    ("Marut",    "storm",         "Storm-wind deities (plural); cognate with Kassite Maruttaš?"),
    ("Soma",     "moon/plant",    "Moon deity and ritual plant"),
    ("Vāyu",    "wind",          "Wind deity"),
    ("Aśvin",   "dawn",          "Twin dawn-horse deities"),
    ("Savitṛ",  "sun",           "Solar deity, the Impeller"),
    ("Viṣṇu",   "preserver",     "Solar aspect in Rigveda; cosmic deity"),
    ("Rudra",    "storm/death",   "Storm deity, proto-Śiva"),
]

# Format: (transcription, meaning_or_None, name_type, source)
SANSKRIT_NAMES = [
    # Kings / heroes from Rigveda
    ("Divodāsa",    "Slave of heaven",              "royal",      "RV; king of Kāśī"),
    ("Sudās",       "Good giver / bountiful",       "royal",      "RV 3.53; Battle of Ten Kings"),
    ("Trasadasyu",  "Terrifier of slaves",          "royal",      "RV; Pūru king"),
    ("Turvaśa",     "Overcoming obstacles",         "royal",      "RV; son of Yayāti"),
    ("Yadu",        None,                           "royal",      "RV; son of Yayāti, ancestor of Yadavas"),
    ("Pūru",        None,                           "royal",      "RV; founder of Pūru dynasty"),
    ("Bharata",     "Bearer / to be maintained",   "royal",      "RV; Bharata tribe"),
    ("Nahuṣa",     None,                           "royal",      "RV; legendary king"),
    ("Yayāti",     None,                           "royal",      "RV; ancestor king"),
    ("Manu",        "Thinker / man",                "personal",   "RV; first human / lawgiver"),
    # Vedic sages (ṛṣi)
    ("Viśvāmitra",  "Friend of all",               "sage",       "RV; founder of Gāthina lineage"),
    ("Vasiṣṭha",   "Most excellent",               "sage",       "RV; rival of Viśvāmitra"),
    ("Agastya",     None,                           "sage",       "RV 1.165-191; southern sage"),
    ("Jamadagni",   "Fire-like power",              "sage",       "RV; father of Paraśurāma"),
    ("Bharadvāja",  "Bearing strength",             "sage",       "RV; prominent ṛṣi"),
    ("Kutsa",       None,                           "personal",   "RV; aided by Indra"),
    ("Vāmadeva",   "Dear to the gods",             "sage",       "RV 4; hymns to Indra/Agni"),
    ("Atri",        "Eater / all-devouring",        "sage",       "RV; one of Saptarṣi"),
    ("Kaṇva",      None,                           "sage",       "RV; prominent ṛṣi lineage"),
    ("Gotama",      "Best ox",                      "sage",       "RV; Gotama lineage"),
    # Theophoric / compound names
    ("Devāpi",     "Ally of the gods",             "theophoric", "RV 10.98; son of Ṛṣṭiṣena"),
    ("Indravāyu",  "Indra and Vāyu",               "theophoric", "RV; dual deity address"),
    ("Mitravinda", "Finding Mitra",                "theophoric", "Vedic context"),
    ("Agnivarna",  "Color of fire",                "theophoric", "Late Vedic / Epic"),
    ("Somadatta",  "Given by Soma",                "theophoric", "Epics / Mahābhārata"),
    ("Indrasena",  "Army of Indra",                "theophoric", "Epic context"),
    ("Varuṇadatta", "Given by Varuṇa",             "theophoric", "Vedic/Epic"),
    ("Agnidatta",  "Given by Agni",                "theophoric", "Vedic/Epic"),
    ("Mitrāvaruṇa", "Mitra and Varuṇa",            "theophoric", "RV; dual deity compound"),
    # Mitanni-Aryan names (crucial for Kassite connection!)
    ("Kikkuli",     "Horse master",                "title",      "Mitanni; horse-training text ca. 1380 BCE"),
    ("Šuttarna",    None,                          "royal",      "Mitanni; phonetically Skt *Sutarṇa"),
    ("Artaśśumara", "Great is the sun",            "royal",      "Mitanni; Skt *Ṛta-smara"),
    ("Indrota",     "Aided by Indra",              "personal",   "Mitanni-Aryan; Skt Indra"),
    ("Biriašura",   "Storm/Warrior power",         "personal",   "Mitanni; contains Aryan element"),
    ("Māttiwāza",  None,                          "royal",      "Mitanni crown prince"),
    # Warriors / common Vedic names
    ("Ṛjrāśva",   None,                           "personal",   "RV; helped by Aśvins"),
    ("Śunaḥśepa",  "Dog's tail",                  "personal",   "RV 1.24-30; sacrificial victim"),
    ("Abhyāvartin", "Returning/recurring",         "personal",   "RV; Cāyamāna king"),
    ("Balbutha",    None,                          "personal",   "RV; patron of Bharadvāja"),
    ("Priyamedha",  "Beloved sacrifice",           "personal",   "RV 8.4; patron"),
    ("Purukutsa",   "Many deeds",                  "royal",      "RV; Pūru king"),
    ("Durmitra",    "Bad ally",                    "personal",   "Vedic; rare"),
    ("Savyaṣṭhi",  None,                          "personal",   "RV"),
    ("Aṃśu",       "Ray of light",                "personal",   "RV; Soma stalk"),
    ("Vandana",     "Praising",                    "personal",   "RV; aided by Aśvins"),
    ("Viśvakarman", "Maker of all",               "personal",   "RV; divine craftsman"),
    ("Turīti",     None,                          "personal",   "RV; minor figure"),
]

# ── Known cognate hypotheses ──────────────────────────────────────────────────
# (kassite_form, cognate_form, cognate_lang, meaning, confidence, scholarly_ref)
KNOWN_COGNATES = [
    # Deity etymologies — the famous Kassite-Aryan connection
    ("Šuriaš",   "Sūrya",   "skt-ved", "Sun deity",
     "high",    "Mayrhofer 1966; Balkan 1954"),
    ("Šuriaš",   "Sūrya",   "skt",     "Sun deity (classical)",
     "high",    "Mayrhofer 1966"),
    ("Maruttaš", "Marut",   "skt-ved", "Storm-wind deity collective",
     "high",    "Mayrhofer 1966; Balkan 1954; Edzard 1960"),
    ("Maruttaš", "Marut",   "skt",     "Storm deity",
     "high",    "Mayrhofer 1966"),
    ("Indaš",    "Indra",   "skt-ved", "Warrior/storm deity",
     "high",    "Mayrhofer 1966; Balkan 1954"),
    ("Indaš",    "Indra",   "skt",     "Chief warrior deity",
     "high",    "Mayrhofer 1966"),
    ("Buriaš",   "Vṛtra",  "skt-ved", "Storm/obstacle deity (contested)",
     "low",     "Balkan 1954; disputed by Edzard"),
    # Hurrian-Kassite comparisons
    ("Indaš",    "Indra",   "hur",     "Storm warrior; *ind- root",
     "medium",  "Diakonoff & Starostin 1986; Speiser 1941"),
    ("Buriaš",   "Tešup",   "hur",     "Storm deity equivalence (functional, not etymological)",
     "low",     "Functional parallel; Edzard 1960"),
    # Name element parallels
    ("saḫ",      "sakha",   "skt-ved", "Friend/companion (semantic parallel)",
     "low",     "Balkan 1954 (speculative)"),
    ("bugaš",    "bhaga",   "skt-ved", "Fortune/god-share",
     "medium",  "Mayrhofer 1966; *bhag- share/apportion"),
]


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_or_create_language(cur: sqlite3.Cursor, iso: str) -> int:
    row = cur.execute("SELECT id FROM languages WHERE iso_code=?", (iso,)).fetchone()
    return row[0] if row else None


def get_or_create_corpus(cur: sqlite3.Cursor, name: str) -> int | None:
    row = cur.execute("SELECT id FROM corpora WHERE name=?", (name,)).fetchone()
    return row[0] if row else None


def compute_cv(name: str) -> str:
    """Simple CV structure: C=consonant, V=vowel."""
    vowels = set("aeiouāīūêâîûàèìò")
    clean = re.sub(r"[\s\-/\(\)\[\]?!0]", "", name.lower())
    return "".join("V" if c in vowels else "C" for c in clean if c.isalpha() or c in vowels)


def insert_name_with_morphology(
    cur: sqlite3.Cursor,
    corpus_id: int,
    transcription: str,
    meaning: str | None,
    name_type: str,
    notes: str,
) -> int:
    cur.execute("""
        INSERT OR IGNORE INTO names (corpus_id, transcription, meaning, name_type, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (corpus_id, transcription, meaning, name_type, notes))
    name_id = cur.execute(
        "SELECT id FROM names WHERE transcription=? AND corpus_id=?",
        (transcription, corpus_id),
    ).fetchone()[0]

    # Basic morphology
    cv = compute_cv(transcription)
    clean = re.sub(r"[\s\-/\(\)\[\]?!0]", "", transcription.lower())
    vowels_in_name = [c for c in clean if c in set("aeiouāīūêâîûàèìò")]
    syllables = len(vowels_in_name)
    skeleton  = "".join(c for c in clean if c not in set("aeiouāīūêâîûàèìò"))

    cur.execute("""
        INSERT OR IGNORE INTO name_morphology
            (name_id, cv_structure, length_chars, syllable_count, consonantal_skeleton)
        VALUES (?, ?, ?, ?, ?)
    """, (name_id, cv, len(clean), syllables, skeleton))

    return name_id


def link_deity(cur: sqlite3.Cursor, name_id: int, deity_name: str, lang_id: int,
               position: str = "final") -> None:
    # Ensure deity exists
    row = cur.execute(
        "SELECT id FROM deities WHERE canonical_name=?", (deity_name,)
    ).fetchone()
    if not row:
        cur.execute(
            "INSERT OR IGNORE INTO deities (canonical_name, language_id) VALUES (?, ?)",
            (deity_name, lang_id),
        )
        deity_id = cur.lastrowid
    else:
        deity_id = row[0]

    cur.execute("""
        INSERT OR IGNORE INTO name_deity_links (name_id, deity_id, position)
        VALUES (?, ?, ?)
    """, (name_id, deity_id, position))


def populate_corpus_stats(cur: sqlite3.Cursor, corpus_id: int, names: list[str]) -> None:
    """Compute and store phoneme/bigram/cluster stats for a corpus."""
    from src.linguistics import analyze_phoneme_inventory, analyze_bigrams

    consonants, vowels = analyze_phoneme_inventory(names)
    bigrams = analyze_bigrams(names)

    # Phoneme frequencies
    all_ph = list(consonants.items()) + list(vowels.items())
    total_ph = sum(v for _, v in all_ph)
    for ph, cnt in all_ph:
        cls = "vowel" if ph in set("aeiouāīūêâîûàèìò") else "consonant"
        pct = round(cnt / total_ph * 100, 2) if total_ph else 0
        cur.execute("""
            INSERT OR IGNORE INTO phoneme_frequencies (corpus_id, phoneme, phoneme_class, count, percentage)
            VALUES (?, ?, ?, ?, ?)
        """, (corpus_id, ph, cls, cnt, pct))

    # Bigram frequencies
    total_bg = sum(bigrams.values())
    for bg, cnt in bigrams.most_common(100):
        pct = round(cnt / total_bg * 100, 2) if total_bg else 0
        cur.execute("""
            INSERT OR IGNORE INTO bigram_frequencies (corpus_id, bigram, count, percentage)
            VALUES (?, ?, ?, ?)
        """, (corpus_id, bg, cnt, pct))

    # Phoneme position stats
    v_init, v_med, v_fin = analyze_vowel_by_position(names)
    for pos_dict, pos_label in [(v_init, "initial"), (v_med, "medial"), (v_fin, "final")]:
        for ph, cnt in pos_dict.items():
            cur.execute("""
                INSERT OR IGNORE INTO phoneme_position_stats (corpus_id, phoneme, position, count)
                VALUES (?, ?, ?, ?)
            """, (corpus_id, ph, pos_label, cnt))

    # Clusters
    all_clusters = []
    for n in names:
        clean = re.sub(r"[\s\-/\(\)\[\]?!0]", "", n.lower())
        all_clusters.extend(_get_clusters(clean))
    cluster_cnt = Counter(all_clusters)
    cluster_classes = dict(analyze_cluster_types(all_clusters))
    sonority = dict(analyze_sonority_slope(all_clusters))
    total_cl = sum(cluster_cnt.values())
    for cl, cnt in cluster_cnt.most_common(50):
        pct = round(cnt / total_cl * 100, 2) if total_cl else 0
        cl_class = cluster_classes.get(cl)
        son_dir  = sonority.get(cl)
        cur.execute("""
            INSERT OR IGNORE INTO cluster_frequencies
                (corpus_id, cluster, cluster_class, sonority_direction, count, percentage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (corpus_id, cl, cl_class, son_dir, cnt, pct))

    # Suffix frequencies
    discovered = discover_suffixes(names)
    total_suf = sum(discovered.values())
    for suf, cnt in discovered.most_common(30):
        pct = round(cnt / total_suf * 100, 2) if total_suf else 0
        cur.execute("""
            INSERT OR IGNORE INTO suffix_frequencies (corpus_id, suffix, count, percentage)
            VALUES (?, ?, ?, ?)
        """, (corpus_id, suf, cnt, pct))

    # Minimal pairs
    pairs = find_minimal_pairs(names)
    for a, b in pairs:
        diff_pos = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        cur.execute("""
            INSERT OR IGNORE INTO minimal_pairs
                (corpus_id, form_a, form_b, diff_position, phoneme_a, phoneme_b)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (corpus_id, a, b, diff_pos + 1, a[diff_pos], b[diff_pos]))

    # Skeleton variant groups
    variants = detect_consonantal_skeleton_variants(names)
    for skeleton, members in variants.items():
        cur.execute("""
            INSERT OR IGNORE INTO skeleton_variant_groups (corpus_id, skeleton)
            VALUES (?, ?)
        """, (corpus_id, skeleton))
        grp_id = cur.execute(
            "SELECT id FROM skeleton_variant_groups WHERE corpus_id=? AND skeleton=?",
            (corpus_id, skeleton),
        ).fetchone()[0]
        for m in members:
            cur.execute("""
                INSERT OR IGNORE INTO skeleton_variant_members (group_id, name_form)
                VALUES (?, ?)
            """, (grp_id, m))


def _get_clusters(name: str) -> list[str]:
    import re as _re
    vowels = set("aeiouāīūêâîûàèìò")
    clean = _re.sub(r"[^a-zāīūêâîûśṣṭḍṅñṇḷḥṃ\u1e00-\u1eff]", "", name.lower())
    clusters = []
    i = 0
    buf = ""
    while i < len(clean):
        if clean[i] not in vowels:
            buf += clean[i]
        else:
            if len(buf) >= 2:
                clusters.append(buf)
            buf = ""
        i += 1
    if len(buf) >= 2:
        clusters.append(buf)
    return clusters


# ── Main seeder ───────────────────────────────────────────────────────────────

def seed(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # ── 1. Add Hurrian language ────────────────────────────────────────────────
    cur.execute("""
        INSERT OR IGNORE INTO languages (iso_code, name, family, script, time_period, notes)
        VALUES ('hur', 'Hurritisch', 'Sprachlich isoliert (verwandt mit Urartäisch)',
                'Keilschrift', 'ca. 2300–1200 BCE',
                'Gesprochen in Nordsyrien, SE-Anatolien, NW-Mesopotamien. Nuzi-Archiv ca. 1500–1350 BCE.')
    """)
    cur.execute("""
        UPDATE languages SET family='Indoarisch', time_period='ca. 1500–200 BCE',
               notes='Vedische Phase ca. 1500–800 BCE; klassisch ca. 500 BCE–200 CE'
        WHERE iso_code='skt'
    """)
    cur.execute("""
        UPDATE languages SET time_period='ca. 1500–800 BCE',
               notes='Sprache des Rigveda und frühvedischer Texte; Mitanni-Arya-Lehnwörter ca. 1400 BCE'
        WHERE iso_code='skt-ved'
    """)

    hur_lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code='hur'"
    ).fetchone()[0]
    ved_lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code='skt-ved'"
    ).fetchone()[0]
    skt_lang_id = cur.execute(
        "SELECT id FROM languages WHERE iso_code='skt'"
    ).fetchone()[0]

    # ── 2. Create corpora ──────────────────────────────────────────────────────
    hur_desc = ("Personal names from the Nuzi archive (Cassin & Glassner 1977; CDLI Nuzi corpus). "
                "Nuzi was an important Hurrian-speaking town under Mitanni suzerainty.")
    cur.execute(
        "INSERT OR IGNORE INTO corpora "
        "(name, language_id, time_period_start, time_period_end, region, description) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Hurrian Personal Names (Nuzi)", hur_lang_id, -1500, -1350,
         "Arrapha / Nuzi (mod. Yorghan Tepe, Iraq)", hur_desc),
    )

    ved_desc = ("Personal names from Rigveda, Atharvaveda, and early Vedic literature. "
                "Includes Mitanni-Arya comparanda (ca. 1400 BCE). "
                "Source: Mayrhofer EWAIA; Witzel 1999; Thieme 1960.")
    cur.execute(
        "INSERT OR IGNORE INTO corpora "
        "(name, language_id, time_period_start, time_period_end, region, description) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Vedic Sanskrit Personal Names", ved_lang_id, -1500, -500,
         "Indian subcontinent (Indus-Ganges plains)", ved_desc),
    )

    hur_corpus_id = cur.execute(
        "SELECT id FROM corpora WHERE name='Hurrian Personal Names (Nuzi)'"
    ).fetchone()[0]
    ved_corpus_id = cur.execute(
        "SELECT id FROM corpora WHERE name='Vedic Sanskrit Personal Names'"
    ).fetchone()[0]

    # ── 3. Add Hurrian deities ─────────────────────────────────────────────────
    for deity_name, deity_type, notes in HURRIAN_DEITIES:
        cur.execute("""
            INSERT OR IGNORE INTO deities (canonical_name, language_id, deity_type, notes)
            VALUES (?, ?, ?, ?)
        """, (deity_name, hur_lang_id, deity_type, notes))

    # ── 4. Seed Hurrian names ──────────────────────────────────────────────────
    print(f"Seeding {len(HURRIAN_NAMES)} Hurrian names...")
    hurrian_transcriptions = []
    for transcription, meaning, name_type, notes in HURRIAN_NAMES:
        name_id = insert_name_with_morphology(
            cur, hur_corpus_id, transcription, meaning, name_type, notes
        )
        hurrian_transcriptions.append(transcription)

        # Auto-link theophoric deities if name is theophoric
        if name_type == "theophoric":
            for deity_name, _, _ in HURRIAN_DEITIES:
                if deity_name.lower() in transcription.lower():
                    pos = "final" if transcription.lower().endswith(deity_name.lower()) else "initial"
                    link_deity(cur, name_id, deity_name, hur_lang_id, pos)

    # ── 5. Add Sanskrit/Vedic deities ─────────────────────────────────────────
    for deity_name, deity_type, notes in SANSKRIT_DEITIES:
        cur.execute("""
            INSERT OR IGNORE INTO deities (canonical_name, language_id, deity_type, notes)
            VALUES (?, ?, ?, ?)
        """, (deity_name, ved_lang_id, deity_type, notes))

    # ── 6. Seed Sanskrit/Vedic names ──────────────────────────────────────────
    print(f"Seeding {len(SANSKRIT_NAMES)} Sanskrit/Vedic names...")
    sanskrit_transcriptions = []
    for transcription, meaning, name_type, source in SANSKRIT_NAMES:
        name_id = insert_name_with_morphology(
            cur, ved_corpus_id, transcription, meaning, name_type, source
        )
        sanskrit_transcriptions.append(transcription)

        # Auto-link theophoric deities
        if name_type == "theophoric":
            for deity_name, _, _ in SANSKRIT_DEITIES:
                deity_clean = deity_name.replace("ṇ", "n").replace("ā", "a").lower()
                trans_clean = transcription.lower()
                if deity_name.lower() in trans_clean or deity_clean in trans_clean:
                    pos = "final" if trans_clean.endswith(deity_name.lower()) else "initial"
                    link_deity(cur, name_id, deity_name, ved_lang_id, pos)

    # ── 7. Seed known cognate sets ────────────────────────────────────────────
    print(f"Seeding {len(KNOWN_COGNATES)} known cognate hypotheses...")
    kas_corpus_id = cur.execute(
        "SELECT id FROM corpora WHERE language_id = (SELECT id FROM languages WHERE iso_code='kas')"
    ).fetchone()[0]

    for kas_form, cog_form, cog_lang, meaning, confidence, ref in KNOWN_COGNATES:
        lang_id = cur.execute(
            "SELECT id FROM languages WHERE iso_code=?", (cog_lang,)
        ).fetchone()
        if not lang_id:
            continue
        lang_id = lang_id[0]

        label = f"{kas_form} ~ {cog_form}"

        # Add to cognate_sets
        cur.execute(
            "INSERT OR IGNORE INTO cognate_sets (label, semantic_field, notes) VALUES (?, ?, ?)",
            (label, meaning, ref),
        )
        set_id = cur.execute(
            "SELECT id FROM cognate_sets WHERE label=?", (label,)
        ).fetchone()[0]

        # Find Kassite name id
        kas_name = cur.execute(
            "SELECT n.id FROM names n JOIN corpora c ON n.corpus_id=c.id "
            "WHERE n.transcription=? AND c.id=?",
            (kas_form, kas_corpus_id),
        ).fetchone()

        # Add to etymologies table (cognate_language_id is FK, not text)
        cur.execute(
            "INSERT OR IGNORE INTO etymologies "
            "(form, language_id, proposed_meaning, cognate_language_id, cognate_form, "
            " confidence, scholarly_ref) "
            "VALUES (?, (SELECT id FROM languages WHERE iso_code='kas'), "
            "        ?, ?, ?, ?, ?)",
            (kas_form, meaning, lang_id, cog_form, confidence, ref),
        )
        etym_id = cur.execute(
            "SELECT id FROM etymologies WHERE form=? AND cognate_form=? AND cognate_language_id=?",
            (kas_form, cog_form, lang_id),
        ).fetchone()
        if etym_id and kas_name:
            cur.execute(
                "INSERT OR IGNORE INTO name_etymology_links (name_id, etymology_id) VALUES (?, ?)",
                (kas_name[0], etym_id[0]),
            )

        # Add cognate members
        kas_lang_id = cur.execute(
            "SELECT id FROM languages WHERE iso_code='kas'"
        ).fetchone()[0]
        cur.execute(
            "INSERT OR IGNORE INTO cognate_members "
            "(cognate_set_id, form, language_id, notes) VALUES (?, ?, ?, ?)",
            (set_id, kas_form, kas_lang_id, "Kassite deity name"),
        )
        cur.execute(
            "INSERT OR IGNORE INTO cognate_members "
            "(cognate_set_id, form, language_id, notes) VALUES (?, ?, ?, ?)",
            (set_id, cog_form, lang_id, ref),
        )

    # ── 8. Compute corpus stats ────────────────────────────────────────────────
    print("Computing Hurrian corpus statistics...")
    populate_corpus_stats(cur, hur_corpus_id, hurrian_transcriptions)

    print("Computing Sanskrit corpus statistics...")
    populate_corpus_stats(cur, ved_corpus_id, sanskrit_transcriptions)

    con.commit()
    con.close()

    print("\n[DONE] Corpus seeding complete.")
    print(f"  Hurrian names:  {len(HURRIAN_NAMES)}")
    print(f"  Sanskrit names: {len(SANSKRIT_NAMES)}")
    print(f"  Cognate sets:   {len(KNOWN_COGNATES)}")


if __name__ == "__main__":
    seed()
