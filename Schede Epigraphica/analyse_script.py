import random
import os

DATEINAME = "text_7572.txt"

FORMELN = {
    # Verben & Stämme
    "uwa'er": "D-Stamm (wârum) | Formel: D-Prät + Ventiv | Bedeutung: Befehl erteilen / aussenden",
    "uštapra": "Št-Stamm (šapārum) | Formel: Št-Perfekt | Bedeutung: Sich gegenseitig schreiben",
    "il-qú-ú": "G-Stamm (leqûm) | Formel: G-Prät, 3.pl.m. | Bedeutung: Sie nahmen",
    "i-la-ap-pa-at": "G-Stamm (lapātum) | Formel: G-Präsens, 3.sg. | Bedeutung: Er berührt (Kehle)",
    "ú-ša-al-pa-tu": "Š-Stamm (lapātum) | Formel: Š-Präsens, 3.pl. | Bedeutung: Sie lassen (die Kehle) berühren",
    
    # Fachbegriffe & Kontext
    "napištam": "Rechtsformel | Kontext: 'Kehle berühren' = Eid ablegen / Vertrag schließen",
    "ṭuppam": "Objekt | Formel: Akkusativ Sg. | Bedeutung: Tontafel (ṣeherum = klein / rabûm = groß)",
    "ṣí-im-da-tim": "Rechtsterminus | Kontext: Verbindliche Verordnung / Staatsvertrag",
    "LÚ ÈŠ.NUN.NA": "Sumerogramm-Kette | Bedeutung: 'Der Mann von Ešnunna' (Königstitel)",
    "DUMU ši-ip-ri": "Sumerogramm-Kette | Bedeutung: Bote / Gesandter (mār šiprim)"
}

def clear_screen():
    os.system('clear')

def lade_text():
    if not os.path.exists(DATEINAME):
        return []
    with open(DATEINAME):
        