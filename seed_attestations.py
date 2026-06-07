"""
seed_attestations.py

Populates `sources` and `name_attestations` tables in ancient_names.db
with primary-source archive data for Kassite personal names.

Sources:
  - Balkan 1954 "Kassitenstudien I" (Nippur, Dur-Kurigalzu archives)
  - Sassmannshausen 2001 "Beiträge zur Verwaltung und Gesellschaft Babyloniens in der Kassitenzeit"
  - Brinkman 1976/1999 "Materials and Studies for Kassite History"
  - Stein 1993 (Nuzi tablets, cross-reference for Hurrian names)

Dates are given in BCE (negative integers for years BCE).
"""

import sqlite3

DB_PATH = "ancient_names.db"

# ---------------------------------------------------------------------------
# Major archive sources
# ---------------------------------------------------------------------------

SOURCES: list[dict] = [
    {
        "short_ref":    "Balkan1954",
        "full_ref":     "Balkan, Kemal. 1954. Kassitenstudien I: Die Sprache der Kassiten. New Haven: American Oriental Society.",
        "source_type":  "scholarly_edition",
        "archive":      "Nippur / Dur-Kurigalzu",
        "tablet_number": None,
        "museum_number": None,
        "notes":        "Primary philological study; lists ~575 Kassite names with morphological analysis.",
    },
    {
        "short_ref":    "Sassmannshausen2001",
        "full_ref":     "Sassmannshausen, Leonhard. 2001. Beiträge zur Verwaltung und Gesellschaft Babyloniens in der Kassitenzeit. Mainz: Philipp von Zabern.",
        "source_type":  "scholarly_edition",
        "archive":      "Nippur",
        "tablet_number": None,
        "museum_number": None,
        "notes":        "Administrative tablets from Nippur. Key source for Kassite names in bureaucratic context.",
    },
    {
        "short_ref":    "Brinkman1976",
        "full_ref":     "Brinkman, J.A. 1976. Materials and Studies for Kassite History, Vol. I. Chicago: Oriental Institute.",
        "source_type":  "scholarly_edition",
        "archive":      "Nippur / Babylon",
        "tablet_number": None,
        "museum_number": None,
        "notes":        "Comprehensive prosopography of Kassite Babylonia; catalogues royal names and administrative personnel.",
    },
    {
        "short_ref":    "Brinkman1999",
        "full_ref":     "Brinkman, J.A. 1999. 'Appendix: Mesopotamian Chronology of the Historical Period.' In Oppenheim, Ancient Mesopotamia. Chicago: Oriental Institute.",
        "source_type":  "scholarly_edition",
        "archive":      "Various",
        "tablet_number": None,
        "museum_number": None,
        "notes":        "Chronological framework for Kassite dynasty; provides regnal years for Kassite kings.",
    },
    {
        "short_ref":    "NippurAdminTablets",
        "full_ref":     "Nippur Administrative Tablets (Kassite period, ca. 1400–1155 BCE). Various museums.",
        "source_type":  "primary_archive",
        "archive":      "Nippur",
        "tablet_number": "PBS 2/2; BE 14; BE 15",
        "museum_number": "UM (University Museum, Philadelphia)",
        "notes":        "Administrative records from Nippur's Kassite administrative center; bulk of Kassite prosopography.",
    },
    {
        "short_ref":    "DurKurigalzu",
        "full_ref":     "Dur-Kurigalzu (modern Aqar Quf) excavation tablets, Iraqi Museum. ca. 1400–1200 BCE.",
        "source_type":  "primary_archive",
        "archive":      "Dur-Kurigalzu",
        "tablet_number": None,
        "museum_number": "IM (Iraq Museum, Baghdad)",
        "notes":        "Royal palace archive; yields Kassite royal names, theophoric compounds, administrative personnel.",
    },
    {
        "short_ref":    "AmarnaTEA",
        "full_ref":     "Tell el-Amarna Letters (EA). ca. 1360–1332 BCE. Berlin, British Museum, Cairo.",
        "source_type":  "primary_archive",
        "archive":      "Amarna (Egypt)",
        "tablet_number": "EA 1–11 (Kassite letters to Egypt)",
        "museum_number": "VAT (Vorderasiatisches Museum Berlin); BM",
        "notes":        "Royal correspondence between Kassite kings and Egyptian pharaohs. Names: Burna-Buriaš II, Kadašman-Enlil I, Kurigalzu II.",
    },
    {
        "short_ref":    "KassiteKingList",
        "full_ref":     "Kassite King List (Babylonian King List A & B). ca. 7th cent. BCE copies of older originals.",
        "source_type":  "king_list",
        "archive":      "Babylon / Nineveh",
        "tablet_number": "BM 33332 (King List A)",
        "museum_number": "BM",
        "notes":        "Provides 36 Kassite royal names with regnal years. Key source for dynasty chronology.",
    },
    {
        "short_ref":    "SynchHistory",
        "full_ref":     "Synchronistic History (Assyrian). ca. 800 BCE. British Museum.",
        "source_type":  "historical_text",
        "archive":      "Nineveh",
        "tablet_number": "BM 92701",
        "museum_number": "BM",
        "notes":        "Lists Kassite-Assyrian synchronisms; mentions Kassite kings Burna-Buriaš, Karaḫardaš, Nazi-Maruttaš.",
    },
]

# ---------------------------------------------------------------------------
# Name attestations: (transcription, source_short_ref, date_text, date_min, date_max, context)
# Dates are BCE years (negative numbers)
# ---------------------------------------------------------------------------

ATTESTATIONS: list[dict] = [
    # Royal names — attested in king lists and historical texts
    {"name": "Gandaš",         "source": "KassiteKingList", "date_text": "ca. 1729–1718 BCE",  "date_min": -1729, "date_max": -1718, "context": "Founder of Kassite dynasty; first attested king."},
    {"name": "Agum",           "source": "KassiteKingList", "date_text": "multiple kings",      "date_min": -1700, "date_max": -1450, "context": "Name borne by several early Kassite kings (Agum I–III)."},
    {"name": "Agum",            "source": "KassiteKingList", "date_text": "ca. 1595 BCE",        "date_min": -1595, "date_max": -1590, "context": "Agum-Kakrime: returned the statue of Marduk from Ḫana."},
    {"name": "Burna-Buriaš",   "source": "AmarnaTEA",       "date_text": "ca. 1359–1333 BCE",   "date_min": -1359, "date_max": -1333, "context": "EA 1–6: correspondence with Amenhotep III and Akhenaten."},
    {"name": "Kadašman-Enlil", "source": "AmarnaTEA",       "date_text": "ca. 1374–1360 BCE",   "date_min": -1374, "date_max": -1360, "context": "EA 1: marriage negotiations with Amenhotep III."},
    {"name": "Kurigalzu",      "source": "DurKurigalzu",    "date_text": "ca. 1400–1375 / 1332–1308 BCE", "date_min": -1400, "date_max": -1308, "context": "Founded Dur-Kurigalzu; two kings bore this name."},
    {"name": "Nazi-Maruttaš",  "source": "SynchHistory",    "date_text": "ca. 1307–1282 BCE",   "date_min": -1307, "date_max": -1282, "context": "Contemporary of Adad-nirari I of Assyria; border treaty."},
    {"name": "kara-ḫardaš",    "source": "SynchHistory",    "date_text": "ca. 1235 BCE",         "date_min": -1237, "date_max": -1232, "context": "Murdered in revolt; succeeded by Nazi-Bugaš."},
    {"name": "šagarakti-enlil","source": "Brinkman1976",    "date_text": "ca. 1186–1172 BCE",   "date_min": -1186, "date_max": -1172, "context": "Kudurru stones document land grants during his reign."},
    {"name": "šagarakti-saḫ",  "source": "Brinkman1976",    "date_text": "ca. 1171–1159 BCE",   "date_min": -1171, "date_max": -1159, "context": "Late Kassite administrative official, Nippur."},
    {"name": "šagarakti-suriyaš","source": "Brinkman1976",  "date_text": "ca. 1245–1233 BCE",   "date_min": -1245, "date_max": -1233, "context": "Built temple of Marduk at Babylon; fought Tukulti-Ninurta I."},
    {"name": "Kaššu",          "source": "Sassmannshausen2001", "date_text": "ca. 1400–1350 BCE", "date_min": -1400, "date_max": -1350, "context": "Nippur administrative tablet; Kassite ethnonym as personal name."},
    {"name": "gab-buriyaš",    "source": "NippurAdminTablets", "date_text": "ca. 1350–1300 BCE", "date_min": -1350, "date_max": -1300, "context": "BE 14: tablet witness at Nippur."},
    {"name": "meli-buriyaš",   "source": "NippurAdminTablets", "date_text": "ca. 1300–1250 BCE", "date_min": -1300, "date_max": -1250, "context": "PBS 2/2: witness in land-sale document, Nippur."},
    {"name": "Nazi-Bugaš",     "source": "SynchHistory",    "date_text": "ca. 1235 BCE",         "date_min": -1237, "date_max": -1227, "context": "Usurper who killed Karaḫardaš; expelled by Kurigalzu II."},
    {"name": "ulam-buriyaš",   "source": "Brinkman1976",    "date_text": "ca. 1533 BCE",         "date_min": -1535, "date_max": -1530, "context": "Conquered Sea-Land dynasty; early Kassite expansion."},
    {"name": "Kaštiliaš",      "source": "KassiteKingList", "date_text": "multiple kings",       "date_min": -1700, "date_max": -1225, "context": "Name borne by 4 Kassite kings; Kaštiliaš IV fought Tukulti-Ninurta I."},
    {"name": "Abi-Rataš",      "source": "NippurAdminTablets", "date_text": "ca. 1350–1300 BCE", "date_min": -1350, "date_max": -1300, "context": "Nippur tablet; minor official."},
    {"name": "Karak-saḫ",      "source": "Sassmannshausen2001", "date_text": "ca. 1400–1350 BCE", "date_min": -1400, "date_max": -1350, "context": "Administrative record; Nippur grain ration recipient."},
    {"name": "kara-indaš",     "source": "KassiteKingList", "date_text": "ca. 1415 BCE",         "date_min": -1420, "date_max": -1410, "context": "Early Kassite king; dedicated temple to Inanna at Uruk."},
    {"name": "kara-šuqamuna",  "source": "KassiteKingList", "date_text": "ca. 1490 BCE",         "date_min": -1500, "date_max": -1480, "context": "Kassite king; name invokes the deity Šuqamuna."},
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed(db_path: str = DB_PATH) -> None:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")

    # Get Kassite corpus id
    kas_corpus_id = con.execute(
        "SELECT c.id FROM corpora c JOIN languages l ON c.language_id = l.id WHERE l.iso_code = 'kas'"
    ).fetchone()[0]

    # ── 1. Clear existing data ─────────────────────────────────────────────
    con.execute("DELETE FROM name_attestations")
    con.execute("DELETE FROM sources")

    # ── 2. Insert sources ─────────────────────────────────────────────────
    print("Inserting sources …")
    source_id_map: dict[str, int] = {}
    for s in SOURCES:
        cur = con.execute(
            """INSERT INTO sources
               (corpus_id, short_ref, full_ref, source_type, archive,
                tablet_number, museum_number, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                kas_corpus_id,
                s["short_ref"], s["full_ref"], s["source_type"], s["archive"],
                s.get("tablet_number"), s.get("museum_number"), s.get("notes"),
            ),
        )
        source_id_map[s["short_ref"]] = cur.lastrowid
    print(f"  Inserted {len(source_id_map)} sources.")

    # ── 3. Insert name attestations ─────────────────────────────────────
    print("Inserting name attestations …")
    matched = 0
    skipped = 0
    for att in ATTESTATIONS:
        # Find name_id — match on transcription prefix (handles partial matches)
        row = con.execute(
            "SELECT id FROM names WHERE LOWER(transcription) = LOWER(?)", (att["name"],)
        ).fetchone()
        if row is None:
            # Try partial match (case-insensitive)
            row = con.execute(
                "SELECT id FROM names WHERE LOWER(transcription) LIKE LOWER(?)",
                (att["name"] + "%",)
            ).fetchone()
        if row is None:
            print(f"  [SKIP] Name not found: {att['name']}")
            skipped += 1
            continue

        name_id = row[0]
        source_id = source_id_map.get(att["source"])
        if source_id is None:
            print(f"  [SKIP] Source not found: {att['source']}")
            skipped += 1
            continue

        con.execute(
            """INSERT INTO name_attestations
               (name_id, source_id, date_text, date_min_year, date_max_year,
                date_calendar, context_notes)
               VALUES (?,?,?,?,?,?,?)""",
            (
                name_id, source_id,
                att["date_text"], att["date_min"], att["date_max"],
                "BCE", att["context"],
            ),
        )
        matched += 1

    con.commit()
    print(f"  Matched: {matched}  |  Skipped (not found): {skipped}")

    # ── 4. Summary query ─────────────────────────────────────────────────
    print("\nTop attested archives:")
    for row in con.execute("""
        SELECT s.archive, COUNT(*) c
        FROM name_attestations na
        JOIN sources s ON na.source_id = s.id
        GROUP BY s.archive ORDER BY c DESC
    """).fetchall():
        print(f"  {row[0]:<30} {row[1]}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    seed()
