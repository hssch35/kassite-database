import os
from collections import Counter

if not os.path.exists('output'):
    os.makedirs('output')
from src.data_handler import load_database, save_database
from src.linguistics import (
    analyze_theophoric_elements,
    isolate_stems,
    split_stem_suffix,
    get_consonant_clusters,
    get_root_vowel,
    analyze_phonetic_classes,
    analyze_positions,
    analyze_cluster_types,
    get_sonority_value,
    analyze_sonority_slope,
    discover_suffixes,
    split_kassite_morphemes,
    # new analyses
    analyze_phoneme_inventory,
    analyze_bigrams,
    analyze_name_length,
    analyze_syllable_distribution,
    analyze_vowel_by_position,
    detect_consonantal_skeleton_variants,
    find_minimal_pairs,
    analyze_theophoric_productivity,
)

from src.visualizer import (plot_vowel_correlation, plot_phonetic_distribution)


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

    stems = [
        entry.get('isolated_stem') 
        for entry in db 
        if entry.get('isolated_stem') and entry.get('isolated_stem') not in ["Unbekannt"]
    ]
    
    
    stem_counts = Counter(stems)
    top_stems = stem_counts.most_common(10)
    
    
    print("\n--- Top 10 der isolierten Wortstämme ---")
    print(f"{'Stamm':<15} | {'Häufigkeit'}")
    print("-" * 30)
    for stem, count in top_stems:
        print(f"{stem:<15} | {count}") 
        
    suffixes = []
    for entry in db: 
        stem = entry.get('isolated_stem')
        if stem and stem not in ["Unbekannt"]:
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
        if root and root not in ["Unbekannt"]:
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
            result = analyze_positions(root)
            if result and result[0] is not None:
                res_start, res_end = result
                starts.append(res_start)
                ends.append(res_end)

    start_counts = Counter(starts)
    end_counts = Counter(ends)

    print("\n--- Phonetik: Bevorzugte Anlaute (Wurzelbeginn) ---")
    for label, count in start_counts.most_common():
            print(f"{label:<15} | {count}")

    print("\n--- Phonetik: Bevorzugte Auslaute (Wurzelende) ---")
    for label, count in end_counts.most_common():
            print(f"{label:<15} | {count}")

    plot_phonetic_distribution(start_counts, "Bevorzugte Anlaute (Wurzelbeginn)", "anlaute")
    plot_phonetic_distribution(end_counts, "Bevorzugte Auslaute (Wurzelende)", "auslaute")
    plot_vowel_correlation(vowel_harm_counts, "vokal_muster")

    print("\n[INFO] Grafiken wurden im Ordner 'output/' gespeichert.")

    all_clusters = []
    for entry in db:
        res = get_consonant_clusters(entry.get('root', ''))
        all_clusters.extend(res)

    clusters_structures = analyze_cluster_types(all_clusters)
    
    print("\n--- Analyse der Cluster-Strukturen (Lautklassen) ---")
    
    sorted_structures = sorted(clusters_structures.items(), key=lambda x: x[1], reverse=True)
    for struct, count in sorted_structures[:5]:
            print(f"{struct:<20} | {count}")
    
    structures = []
    for entry in db:
        struct = entry.get('structure')
        if struct:
            structures.append(struct)
    
    struct_counts = Counter(structures)
    
    print("\n--- Top 10 Silbenstrukturen (aus der DB) ---")
    for s, count in struct_counts.most_common(10):
        
        percentage = (count / len(structures)) * 100
        print(f"{s:<20} | {count:>3} ({percentage:.1f}%)")
        
    save_database(db, "data/kassite_names_db_enriched.json")
    
    print("\n[SUCCESS] Alle Analysedaten (Roots, Suffixe, Cluster) wurden dauerhaft gespeichert.")

    all_names = [e.get('transcription') for e in db if e.get('transcription')]
    
    found_endings_stats = discover_suffixes(all_names)
    auto_suffixes = [suff for suff, count in found_endings_stats.items() if count >= 5]
    
    print(f"\n--- Automatisch entdeckte Suffix-Kandidaten: {len(auto_suffixes)} ---")
    print(", ".join(auto_suffixes))
    
    print("Starte Zerlegung der Namen in Wurzel + Suffix...")
    
    
    erfolgreich_zerlegt = 0
    for entry in db:
        name = entry.get('transcription')
        if name: 
            
            root_morph, suffix_morph = split_kassite_morphemes(name, custom_suffixes=auto_suffixes)
            
            
            entry['morpheme_root'] = root_morph
            entry['morpheme_suffix'] = suffix_morph
            
            if root_morph and suffix_morph:
                erfolgreich_zerlegt += 1
    
    
    print(f"[DEBUG] Namen mit gefundenen Morphemen: {erfolgreich_zerlegt}")

    
    all_names_cleaned = []
    for entry in db:
        name = entry.get('transcription', '')
        gods = entry.get('detected_gods', [])
        cleaned_name = name
        for g in gods:
            cleaned_name = cleaned_name.replace(g, "")
        if len(cleaned_name) > 3:
            all_names_cleaned.append(cleaned_name)

    save_database(db, "data/kassite_names_db_enriched.json")
    print("[SUCCESS] Morphem-Analyse abgeschlossen und gespeichert.")

    # ------------------------------------------------------------------
    # New analyses
    # ------------------------------------------------------------------
    all_transcriptions = [e.get('transcription') for e in db if e.get('transcription')]

    # 1. Phoneme inventory
    consonant_counts, vowel_counts = analyze_phoneme_inventory(all_transcriptions)
    print("\n--- Rekonstruiertes Phonem-Inventar (Konsonanten) ---")
    print(f"{'Phonem':<10} | {'Häufigkeit'}")
    print("-" * 25)
    for ph, cnt in consonant_counts.most_common():
        print(f"{ph:<10} | {cnt}")

    print("\n--- Vokal-Inventar ---")
    for v, cnt in vowel_counts.most_common():
        print(f"{v:<10} | {cnt}")

    # 2. Bigram frequencies (top 15 — reveals phonotactic preferences)
    bigrams = analyze_bigrams(all_transcriptions)
    print("\n--- Top 15 Bigramme (Phonotaktik) ---")
    print(f"{'Bigramm':<10} | {'Häufigkeit'}")
    print("-" * 25)
    for bg, cnt in bigrams.most_common(15):
        print(f"{bg:<10} | {cnt}")

    # 3. Name length distribution
    length_dist = analyze_name_length(all_transcriptions)
    print("\n--- Namenslängen-Verteilung (Zeichen) ---")
    for length in sorted(length_dist.keys()):
        bar = '#' * length_dist[length]
        print(f"{length:>3} Zeichen: {length_dist[length]:>4}  {bar}")

    # 4. Syllable count distribution
    syllable_dist = analyze_syllable_distribution(all_transcriptions)
    print("\n--- Silbenanzahl-Verteilung ---")
    for nsyl in sorted(syllable_dist.keys()):
        print(f"{nsyl} Silbe(n): {syllable_dist[nsyl]}")

    # 5. Vowel position analysis
    v_initial, v_medial, v_final = analyze_vowel_by_position(all_transcriptions)
    print("\n--- Vokalposition: anlautend | medial | auslautend ---")
    all_vowels = sorted(set(list(v_initial) + list(v_medial) + list(v_final)))
    print(f"{'Vokal':<8} | {'Anlaut':>8} | {'Medial':>8} | {'Auslaut':>8}")
    print("-" * 42)
    for v in all_vowels:
        print(f"{v:<8} | {v_initial.get(v, 0):>8} | {v_medial.get(v, 0):>8} | {v_final.get(v, 0):>8}")

    # 6. Consonantal skeleton variants (possible scribal alternations)
    variants = detect_consonantal_skeleton_variants(all_transcriptions)
    print(f"\n--- Konsonantenskelett-Varianten ({len(variants)} Gruppen) ---")
    for skeleton, name_variants in sorted(variants.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  [{skeleton}]: {', '.join(name_variants)}")

    # 7. Minimal pairs
    pairs = find_minimal_pairs(all_transcriptions)
    print(f"\n--- Minimale Paare ({len(pairs)} gefunden) ---")
    for a, b in pairs[:20]:
        diff_pos = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        print(f"  {a}  /  {b}  (Pos {diff_pos + 1}: '{a[diff_pos]}' vs '{b[diff_pos]}')")

    # 8. Theophoric productivity (deity popularity as name-forming element)
    god_productivity = analyze_theophoric_productivity(db)
    print("\n--- Theophore Produktivität (Götter × einzigartige Stämme) ---")
    print(f"{'Gottheit':<20} | {'Einzigartige Stämme'}")
    print("-" * 42)
    for god, count in sorted(god_productivity.items(), key=lambda x: -x[1]):
        print(f"{god:<20} | {count}")

    save_database(db, "data/kassite_names_db_enriched.json")
    print("\n[SUCCESS] Alle erweiterten Analysen abgeschlossen und gespeichert.")


if __name__ == "__main__":
    main()
