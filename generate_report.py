import json
from collections import Counter
from src.linguistics import (
    analyze_positions, 
    analyze_sonority_slope, 
    get_consonant_clusters,
    analyze_cluster_types
)

def generate_markdown_table(data_dict, title, headers=("Kategorie", "Anzahl", "Anteil %")):
    """Erzeugt eine formatierte Markdown-Tabelle."""
    total = sum(data_dict.values())
    if total == 0: return f"\n### {title}\nKeine Daten verfügbar."
    
    sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
    table = [f"\n### {title}", f" | {headers[0]:<25} | {headers[1]:>8} | {headers[2]:>10} |", f"|{'-'*27}|{'-'*10}|{'-'*12}|"]
    
    for key, value in sorted_items[:15]:
        percentage = (value / total) * 100
        table.append(f"| {str(key):<25} | {value:>8} | {percentage:>9.1f}% |")
    return "\n".join(table)

def run_report():
    print("--- Generiere tabellarischen Linguistik-Bericht ---")
    
    try:
        with open("data/kassite_names_db_enriched.json", "r", encoding="utf-8") as f:
            db = json.load(f)
    except FileNotFoundError:
        print("Fehler: Datenbank nicht gefunden. Bitte zuerst main.py ausführen!")
        return
    
    
    starts = []
    ends = []
    all_clusters = [] 
    cv_structures = []
    morpheme_roots = []
    morpheme_suffixes = []
    theophoric_counts = Counter()
    
    for entry in db:
        if entry.get('detected_gods'):
            for god in entry['detected_gods']:
                theophoric_counts[god] += 1

        root = entry.get('root')
        if root and root not in ["Unbekannt", "Unebkannt"]:
            res = analyze_positions(root)
            if res and res[0]:
                starts.append(res[0].upper()) 
                ends.append(res[1].lower())
            
            clusters = get_consonant_clusters(root)
            all_clusters.extend(clusters)
        
        if entry.get('structure'):
            cv_structures.append(entry['structure'])
        
        if entry.get('morpheme_root'):
            morpheme_roots.append(entry['morpheme_root'].capitalize())
        if entry.get('morpheme_suffix'):
            morpheme_suffixes.append(entry['morpheme_suffix'].lower())
            
    
    sonority_stats = analyze_sonority_slope(all_clusters)
    cluster_strings = ["".join(c) for c in all_clusters]
    cluster_counts = Counter(cluster_strings)
    cluster_type_data = analyze_cluster_types(all_clusters)
    
    suffix_to_roots = {}
    for entry in db:
        r = entry.get('morpheme_root')
        s = entry.get('morpheme_suffix')
        if r and s:
            r = r.capitalize()
            s = s.lower()
            if s not in suffix_to_roots:
                suffix_to_roots[s] = []
            if r not in suffix_to_roots[s]: 
                suffix_to_roots[s].append(r)

    report = []
    report.append("# Kassitische Onomastik\n")
    report.append(f"Analysierte Datensätze: {len(db)}")

    report.append(generate_markdown_table(theophoric_counts, "Theophore Elemente (Götternamen)"))
    report.append(generate_markdown_table(Counter(starts), "Bevorzugte Anlaute"))
    report.append(generate_markdown_table(Counter(ends), "Bevorzugte Auslaute"))
    report.append(generate_markdown_table(cluster_counts, "Top Konsonanten-Cluster"))
    report.append(generate_markdown_table(cluster_type_data, "Struktur der Lautklassen-Cluster"))
    report.append(generate_markdown_table(sonority_stats, "Sonoritäts-Profil (Cluster-Tendenz)"))
    report.append(generate_markdown_table(Counter(cv_structures), "Top Silbenstrukturen (CV-Muster)"))
    report.append(generate_markdown_table(Counter(morpheme_roots), "Häufigste Morphem-Wurzeln (Top 15)"))
    report.append(generate_markdown_table(Counter(morpheme_suffixes), "Häufigste Suffixe (Automatisch erkannt)"))
    report.append("\n## Vertiefende Suffix-Analyse: Wurzel-Kombinationen")
    report.append("| Suffix | Anzahl Belege | Beispiel-Wurzeln (Kollokationen) |")
    report.append("| :--- | :---: | :--- |")
    
    sorted_suffixes = sorted(Counter(morpheme_suffixes).items(), key=lambda x: x[1], reverse=True)
    
    for suff, count in sorted_suffixes[:20]:
        roots_list = ", ".join(suffix_to_roots.get(suff, [])[:5]) 
        report.append(f"| **-{suff}** | {count} | {roots_list} ... |")

    with open("output/phonetik_tabelle.md", "w", encoding="utf-8") as f:
            f.write("\n".join(report))

    print("\n[INFO] Der tabellarische Bericht wurde in 'output/phonetik_tabelle.md' gespeichert.")

if __name__ == "__main__":
    run_report()