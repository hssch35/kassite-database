import re
from collections import Counter


def analyze_theophoric_elements(data, gods_list):
    """
    Untersucht eine Liste von Namen auf Götter-Elemente.
    """
    results = []
    
    for entry in data:
        name = entry.get('transcription','').lower()
        search_name = name.replace('š', 's').replace('ḫ', 'h').replace('ṣ', 's')
        
        found_gods = []
        for god in gods_list:
            god_clean = god.lower().replace('š', 's').replace('ḫ', 'h').replace('ṣ', 's')
            
            if god_clean in search_name:
                found_gods.append(god)
        
        if found_gods:
            results.append({
                'name': entry.get('transcription'),
                'gods': list(set(found_gods)), 
                'position': 'Anfang' if search_name.startswith(found_gods[0].lower().replace('š', 's')) else "Ende/Mitte"
            })
    return results

def isolate_stems(name, detected_gods):
    """
    Isoliert den Wortstamm und entfernt radikal Sonderzeichen, 
    Bindestriche und grammatikalische Endungen.
    """
    stem = name.lower()
    for god in detected_gods:
        stem = stem.replace(god.lower(), "").replace("-", "")
        
        stem = re.sub(r'[^a-zšḫṣṭ]', ' ', stem)

        parts = stem.split()
        if not parts:
            return "Unbekannt"

        main_stem = max(parts, key=len)

        if len(main_stem) <= 2:
            return "Unbekannt"
        
    return main_stem.capitalize()

def split_stem_suffix(stem):
    """
    Trennt den Endvokal vom restlichen Stamm.
    Beispiel: 'Burna' -> ('Burn', 'a'), 'Nazi' -> ('Naz', 'i')
    """
    if not stem or len(stem) < 3:
        return stem, ""

    if stem[-1].lower() in "aeiou":
        root = stem[:-1]
        suffix = stem [-1]
        return root,suffix
    
    return stem, ""

def get_consonant_clusters(text):
    """
    Extrahiert alle Paare von aufeinanderfolgenden Konsonanten.
    """
    vowels ="aeiou"
    
    clusters = re.findall(r'[^aeiou]{2,}', text.lower())
    return clusters

def get_root_vowel(root):
    """Extrahiert den letzten Vokal innerhalb der Wurzel."""
    vowels = re.findall(r'[aeiou]', root.lower())
    return vowels[-1] if vowels else None

def analyze_phonetic_classes(text):
    """
    Klassifiziert die Laute einer Wurzel in Gruppen.
    """
    classes = {
        'Labiale':   set('pbmf'),
        'Dentale':   set('tdz'),
        'Nasale':    set('nm'),
        'Liquidae':  set('rl'),
        'Velare':    set('kgx') | {'ḫ'},
        'Sibilanten': set('sz') | {'š'},
    }

    found_classes = []
    for char in text.lower():
        for label, chars in classes.items():
            if char in chars:
                found_classes.append(label)
                break
    return found_classes
    
def analyze_cluster_types(clusters):
    """Kategorisiert Konsonanten-Cluster nach ihren Lautklassen."""
    categories = {
        'r': 'Liquida', 'l': 'Liquida',
        'n': 'Nasale', 'm': 'Nasale',
        'b': 'Labiale', 'p': 'Labiale', 'f': 'Labiale',
        'd': 'Dentale', 't': 'Dentale', 'z': 'Dentale',
        'g': 'Velare', 'k': 'Velare', 'ḫ': 'Velare', 'x': 'Velare',
        'š': 'Sibilanten', 's': 'Sibilanten',
    }
    
    structure_counts = {}
    for cluster in clusters:
        if len(cluster) == 2:
            c1 = categories.get(cluster[0].lower(), 'Andere')
            c2 = categories.get(cluster[1].lower(), 'Andere')
            struct = f"{c1}+{c2}"
            structure_counts[struct] = structure_counts.get(struct, 0) + 1
            
    return structure_counts


def analyze_positions(root):
    if not root or len(root) < 2:
        return None, None
    return root[0].lower(), root[-1].lower()

def get_sonority_value(char):
    char = char.lower()
    scores = {
        'p': 1, 't': 1, 'k': 1, 'b': 1, 'd': 1, 'g': 1,
        'f': 2, 's': 2, 'š': 2, 'z': 2,
        'm': 3, 'n': 3,
        'l': 4, 'r': 4,
        'a': 5, 'e': 5, 'i': 5, 'o': 5, 'u': 5
    }
    return scores.get(char, 0)

def analyze_sonority_slope(clusters):
    slopes = {"Absteigend": 0, "Aufsteigend": 0, "Plateau": 0}
    for c in clusters:
        if len(c) >= 2:
            v1 = get_sonority_value(c[0])
            v2 = get_sonority_value(c[1])
            if v1 > v2:
                slopes["Absteigend"] += 1
            elif v1 < v2:
                slopes["Aufsteigend"] += 1
            else:
                slopes["Plateau"] += 1
    return slopes

def discover_suffixes(names_list, min_length=2, max_length=4):
    """
    Findet automatisch die häufigsten Wortendungen in einer Liste von Namen.
    """
    all_endings = []
    for name in names_list:
        if not name or len(name) < 5: continue
        
        for n in range(min_length, max_length + 1):
            ending = name[-n:].lower()
            all_endings.append(ending)
    return Counter(all_endings)

def split_kassite_morphemes(name, custom_suffixes=None):
    """
    Zerlegt einen Namen in Wurzel und Suffix basierend auf einer Liste von Kandidaten.
    Verwendet das 'Longest Match'-Prinzip (längste Suffixe zuerst).
    """
    if not name or len(name) < 4:
        
        return name, None
    
    
    if custom_suffixes is None:
        suffixes = ['aš', 'iaš', 'ak', 'i', 'a', 'u']
    else:
        suffixes = custom_suffixes
    
    
    suffixes = sorted(suffixes, key=len, reverse=True)
    
    name_low = name.lower()
    
    for suff in suffixes:
        if name_low.endswith(suff.lower()):
            root = name[:-len(suff)]
            return root, suff

    return name, None


# ---------------------------------------------------------------------------
# New analyses (added for deeper decipherment research)
# ---------------------------------------------------------------------------

_VOWELS = set('aeiou')
_SPECIAL_CHARS = set('šḫṣṭ')


def _clean_name(name: str) -> str:
    """Lowercase, strip hyphens and spaces; keep special Kassite chars."""
    return re.sub(r'[\s\-]', '', name.lower())


def analyze_phoneme_inventory(names: list) -> tuple[Counter, Counter]:
    """
    Reconstruct the attested consonant and vowel inventory from the corpus.
    Returns (consonant_counts, vowel_counts).
    """
    consonants: Counter = Counter()
    vowels: Counter = Counter()
    for name in names:
        if not name:
            continue
        for ch in _clean_name(name):
            if ch in _VOWELS:
                vowels[ch] += 1
            elif ch.isalpha() or ch in _SPECIAL_CHARS:
                consonants[ch] += 1
    return consonants, vowels


def analyze_bigrams(names: list) -> Counter:
    """
    Character bigram frequencies across all names.
    Useful for discovering preferred phonotactic sequences.
    """
    bigrams: Counter = Counter()
    for name in names:
        if not name:
            continue
        cleaned = _clean_name(name)
        for i in range(len(cleaned) - 1):
            bigrams[cleaned[i:i+2]] += 1
    return bigrams


def analyze_name_length(names: list) -> Counter:
    """Distribution of name lengths (in characters, hyphens excluded)."""
    lengths: Counter = Counter()
    for name in names:
        if not name:
            continue
        lengths[len(_clean_name(name))] += 1
    return lengths


def analyze_syllable_distribution(names: list) -> Counter:
    """
    Estimate syllable counts per name (each vowel nucleus = one syllable).
    Gives a sense of whether Kassite names are mono-, bi-, or trisyllabic.
    """
    counts: Counter = Counter()
    for name in names:
        if not name:
            continue
        n_syllables = len(re.findall(r'[aeiou]', name.lower()))
        counts[n_syllables] += 1
    return counts


def analyze_vowel_by_position(names: list) -> tuple[Counter, Counter, Counter]:
    """
    Which vowels appear word-initially, medially, and word-finally?
    Helps detect vowel harmony or positional restrictions.
    Returns (initial_counts, medial_counts, final_counts).
    """
    initial: Counter = Counter()
    medial: Counter = Counter()
    final: Counter = Counter()
    for name in names:
        if not name:
            continue
        cleaned = _clean_name(name)
        if not cleaned:
            continue
        if cleaned[0] in _VOWELS:
            initial[cleaned[0]] += 1
        if cleaned[-1] in _VOWELS:
            final[cleaned[-1]] += 1
        for ch in cleaned[1:-1]:
            if ch in _VOWELS:
                medial[ch] += 1
    return initial, medial, final


def detect_consonantal_skeleton_variants(names: list) -> dict:
    """
    Groups names by their consonantal skeleton (vowels stripped).
    Names sharing a skeleton are likely morphological variants or scribal alternations.
    Only groups with ≥2 members are returned.
    """
    groups: dict = {}
    for name in names:
        if not name:
            continue
        skeleton = re.sub(r'[aeiou\s\-]', '', name.lower())
        groups.setdefault(skeleton, []).append(name)
    return {k: sorted(set(v)) for k, v in groups.items() if len(set(v)) > 1}


def find_minimal_pairs(names: list) -> list:
    """
    Find pairs of names that differ by exactly one character substitution
    (same length, Hamming distance = 1).  Useful for phonological analysis.
    """
    cleaned = list({_clean_name(n) for n in names if n})
    pairs = []
    for i in range(len(cleaned)):
        for j in range(i + 1, len(cleaned)):
            a, b = cleaned[i], cleaned[j]
            if len(a) == len(b):
                diffs = sum(x != y for x, y in zip(a, b))
                if diffs == 1:
                    pairs.append((a, b))
    return pairs


def analyze_theophoric_productivity(db: list) -> dict:
    """
    For each detected deity, count how many unique personal stems it combines with.
    High productivity suggests an active, socially prominent deity.
    """
    god_stems: dict = {}
    for entry in db:
        gods = entry.get('detected_gods', [])
        stem = entry.get('isolated_stem')
        if not stem or stem == 'Unbekannt':
            continue
        for god in gods:
            god_stems.setdefault(god, set()).add(stem.lower())
    return {god: len(stems) for god, stems in god_stems.items()}