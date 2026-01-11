import os
if not os.path.exists('output'):
    os.makedirs('output')
from src.data_handler import load_database, save_database
from src.linguistics import analyze_theophoric_elements, isolate_stems, split_stem_suffix, get_consonant_clusters, get_root_vowel, analyze_phonetic_classes, analyze_positions
from src.visualizer import plot_phonetic_distribution, plot_vowel_correlation


def main():
    print("--- Start der Analyse ---")
    
    file_path = "data/kassite_names_db_analyzed.json"
    db = load_database(file_path)
    
    if not db:
        print("Die Datenbank scheint leer zu sein oder wurde nicht gefunden.")
        return 
    
    print(f"{len(db)} Einträge erfolgreich geladen.")
    
    kassite_gods = [ 
        "Bugaš", "bugašu", "Sugab", "Šugab", 
        "Šuriaš", "suriaš", "shuriash",
        "Maruttaš", "marutash",
        "Buriaš", "buriyaš", "burash",
        "Indaš", "indas",
        "Hala", "Sah", "saḫ",
        "Harbe", "enlil" 
    ]
    
    results = analyze_theophoric_elements(db, kassite_gods)
    for entry in db:
        name = entry.get('transcription')
        match = next((item for item in results if item['name'] == name), None)
        if match:
            entry['detected_gods'] = match['gods']
            entry['god_position'] = match['position']
            entry['isolated_stem'] = isolate_stems(name, match['gods'])
        else:
            entry ['isolated_stem'] = None 
    
    save_database(db, "data/kassite_names_db_enriched.json")
    print(f"Angereicherte Datenbank mit {len(results)} Götter-Tags gespeichert.")
    
    save_database(db, "data/kassite_names_db_enriched.json")
    print(f"Angereicherte Datenbank gespeichert.")

    
    from collections import Counter
    
    
    stems = [
        entry.get('isolated_stem') 
        for entry in db 
        if entry.get('isolated_stem') and entry.get('isolated_stem') not in ["Unbekannt", "Unebkannt"]
    ]
    
    
    stem_counts = Counter(stems)
    top_stems = stem_counts.most_common(10)
    
    
    print("\n--- Top 10 der isolierten Wortstämme ---")
    print(f"{'Stamm':<15} | {'Häufigkeit'}")
    print("-" * 30)
    for stem, count in top_stems:
        print(f"{stem:<15} | {count}") 
        
    morphology_results = []

    suffixes = []
    for entry in db: 
        stem = entry.get('isolated_stem')
        if stem and stem not in ["Unbekannt", "Unebkannt"]:
            root, suffix = split_stem_suffix(stem)
            entry['root'] = root
            entry['suffix'] = suffix
            if suffix:
                suffixes.append(suffix)

    suffix_counts = Counter(suffixes)
    print("\n--- Analyse der Stamm-Endungen (Suffixe) ---")
    for suff, count in suffix_counts.most_common():
        print(f"Endung -{suff}: {count} Treffer")
    
    roots = []
    for entry in db:
        root = entry.get('root')
        if root and root not in ["Unbekannt", "Unebkannt"]:
            roots.append(root)
    
    root_counts = Counter(roots)
    
    print("\n--- Top 10 der reinen Wortwurzeln (ohne Vokal) ---")
    print(f"{'Wurzel':<15} | {'Häufigkeit'}")
    print("-" * 30)
    for root, count in root_counts.most_common(10):
        print(f"{root:<15} | {count}")
    
    all_clusters = []
    for entry in db:
        root = entry.get('root')
        if root:
            clusters = get_consonant_clusters(root)
            all_clusters.extend(clusters)
    
    cluster_counts = Counter(all_clusters)
    
    print("\n--- Top 10 der Konsonanten-Cluster (Phonologie) ---")
    print(f"{'Cluster':<15} | {'Häufigkeit'}")
    print("-" * 30)
    for cluster, count in cluster_counts.most_common(10):
        print(f"{cluster:<15} | {count}")
    
    vowel_pairs = []
    for entry in db:
        root = entry.get('root')
        suffix = entry.get('suffix')
        
        if root and suffix:
            root_vowel = get_root_vowel(root)
            if root_vowel:
                
                vowel_pairs.append(f"{root_vowel} -> {suffix}")
    
    vowel_harm_counts = Counter(vowel_pairs)
    
    print("\n--- Vokal-Korrelation (Wurzel -> Suffix) ---")
    print(f"{'Muster':<15} | {'Häufigkeit'}")
    print("-" * 30)
    for pattern, count in vowel_harm_counts.most_common():
        print(f"{pattern:<15} | {count}")

    all_phonetic_classes = []
    for entry in db:
        root = entry.get('root')
        if root:
            all_phonetic_classes.extend(analyze_phonetic_classes(root))
            
    class_counts = Counter(all_phonetic_classes)
    
    print("\n--- Verteilung der Lautklassen ---")
    for label, count in class_counts.most_common():
        print(f"{label:<15} | {count}")
    
    starts = []
    ends = []
    
    
    for entry in db:
        root = entry.get('root')
        if root:
            res_start, res_end = analyze_positions(root)
            if res_start:
                starts.append(res_start)
            if res_end:
                ends.append(res_end)

    
    start_counts = Counter(starts)
    end_counts = Counter(ends)

    print("\n--- Phonetik: Bevorzugte Anlaute (Wurzelbeginn) ---")
    if not starts:
        print("Keine Daten gefunden. Überprüfe, ob entry['root'] gespeichert wird!")
    else:
        for label, count in start_counts.most_common():
            print(f"{label:<15} | {count}")

    print("\n--- Phonetik: Bevorzugte Auslaute (Wurzelende) ---")
    for label, count in end_counts.most_common():
        print(f"{label:<15} | {count}")

    plot_phonetic_distribution(start_counts, "Bevorzugte Anlaute (Wurzelbeginn)", "anlaute")
    plot_phonetic_distribution(end_counts, "Bevorzugte Auslaute (Wurzelende)", "auslaute")
    plot_vowel_correlation(vowel_harm_counts, "vokal_muster")

    print("\n[INFO] Grafiken wurden im Ordner 'output/' gespeichert.")

if __name__ == "__main__":
    main()
