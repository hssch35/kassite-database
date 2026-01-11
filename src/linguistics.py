import re
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
            return "Unebkannt"
        
        main_stem = max(parts, key=len)
        
        if len(main_stem) <= 2:
            return "Unebkannt"
        
    return main_stem.capitalize()

def split_stem_suffix(stem):
    """
    Trennt den Endvokal vom restlichen Stamm.
    Beispiel: 'Burna' -> ('Burn', 'a'), 'Nazi' -> ('Naz', 'i')
    """
    if not stem or len(stem) < 3:
        return stem, ""
    
    vowels = "aeiouyš"
    
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
        'Labiale': 'pbmf',      
        'Dentale': 'tdnsz',     
        'Velare': 'kgḫx',       
        'Sibilanten': 'šszz'    
    }
    
    found_classes = []
    for char in text.lower():
        for label, chars in classes.items():
            if char in chars:
                found_classes.append(label)
        return found_classes
    
def analyze_positions(root):
    if not root or not isinstance(root, str):
        return None, None
    
    
    clean_root = "".join(filter(str.isalpha, root))
    
    if len(clean_root) == 0:
        return None, None

    classes = {
        'Labiale': 'pbmf',
        'Dentale': 'tdnsz',
        'Velare': 'kgḫx',
        'Sibilanten': 'šsž'
    }  
def get_class(char):
        c = char.lower()
        for label, chars in classes.items():
            if c in chars:
                return label
        return "Vokal/Sonstige"

    
        return get_class(clean_root[0]), get_class(clean_root[-1])

def analyze_cluster_types(clusters):
    """Kategorisiert Konsonanten-Cluster nach ihren Lautklassen."""
    categories = {
        'r': 'Liquida', 'l': 'Liquida',
        'n': 'Nasale', 'm': 'Nasale',
        'b': 'Labiale', 'p': 'Labiale',
        'd': 'Dentale', 't': 'Dentale',
        'g': 'Velare', 'k': 'Velare',
        'š': 'Sibilanten', 's': 'Sibilanten'
    }
    
    structure_counts = {}
    for cluster in clusters:
        if len(cluster) == 2:
            c1 = categories.get(cluster[0].lower(), 'Andere')
            c2 = categories.get(cluster[1].lower(), 'Andere')
            struct = f"{c1}+{c2}"
            structure_counts[struct] = structure_counts.get(struct, 0) + 1
            
    return structure_counts
