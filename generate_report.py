import json
import os
from collections import Counter
from src.linguistics import (
    analyze_positions,
    analyze_sonority_slope,
    get_consonant_clusters,
    analyze_cluster_types,
    analyze_phoneme_inventory,
    analyze_bigrams,
    analyze_name_length,
    analyze_syllable_distribution,
    analyze_vowel_by_position,
    detect_consonantal_skeleton_variants,
    find_minimal_pairs,
    analyze_theophoric_productivity,
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

    db_path = "data/kassite_names_db_enriched.json"
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            db = json.load(f)
    except FileNotFoundError:
        print(f"Fehler: Datenbank nicht gefunden unter '{db_path}'. Bitte zuerst main.py ausführen!")
        return
    
    # Listen initialisieren
    starts, ends, all_clusters, cv_structures = [], [], [], []
    morpheme_roots, morpheme_suffixes = [], []
    theophoric_counts = Counter()
    
    for entry in db:
        if entry.get('detected_gods'):
            for god in entry['detected_gods']:
                theophoric_counts[god] += 1

        root = entry.get('root')
        if root and root not in ["Unbekannt"]:
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
    cluster_counts = Counter(all_clusters)
    cluster_type_data = analyze_cluster_types(all_clusters)
    
    
    suffix_to_roots = {}
    for entry in db:
        r = entry.get('morpheme_root')
        s = entry.get('morpheme_suffix')
        if r and s:
            r, s = r.capitalize(), s.lower()
            if s not in suffix_to_roots: suffix_to_roots[s] = []
            if r not in suffix_to_roots[s]: suffix_to_roots[s].append(r)
    
    
    root_to_suffixes = {}
    for entry in db:
        r = entry.get('morpheme_root')
        s = entry.get('morpheme_suffix') 
        if r and s:
            r, s = r.capitalize(), s.lower()
            if r not in root_to_suffixes: root_to_suffixes[r] = []
            if s not in root_to_suffixes[r]: root_to_suffixes[r].append(s)
    
    root_productivity = {r: len(s_list) for r, s_list in root_to_suffixes.items()}

    
    # LLM-enriched fields
    llm_semantic_fields = Counter()
    llm_confidence = Counter()
    llm_entries = []

    for entry in db:
        la = entry.get("llm_analysis")
        if la:
            if la.get("semantic_field"):
                llm_semantic_fields[la["semantic_field"]] += 1
            if la.get("confidence"):
                llm_confidence[la["confidence"]] += 1
            llm_entries.append(entry)

    # New analyses
    all_transcriptions = [e.get('transcription') for e in db if e.get('transcription')]
    consonant_counts, vowel_counts = analyze_phoneme_inventory(all_transcriptions)
    bigrams = analyze_bigrams(all_transcriptions)
    length_dist = analyze_name_length(all_transcriptions)
    syllable_dist = analyze_syllable_distribution(all_transcriptions)
    v_initial, v_medial, v_final = analyze_vowel_by_position(all_transcriptions)
    skeleton_variants = detect_consonantal_skeleton_variants(all_transcriptions)
    minimal_pairs = find_minimal_pairs(all_transcriptions)
    god_productivity = analyze_theophoric_productivity(db)

    total_names = len(db)
    morphemes_found = sum(1 for e in db if e.get('morpheme_root') and e.get('morpheme_suffix'))
    success_rate = (morphemes_found / total_names) * 100 if total_names > 0 else 0
    llm_enriched = len(llm_entries)

    report = ["# Kassite Onomastics — Linguistic Report\n"]
    report.append("**Dataset Overview:**")
    report.append(f"- Total Names Analyzed: {total_names}")
    report.append(f"- Morphemes Successfully Identified: {morphemes_found} ({success_rate:.1f}%)")
    report.append(f"- LLM-Enriched Entries: {llm_enriched}")
    report.append("")
    report.append("---")
    report.append(generate_markdown_table(theophoric_counts, "Theophore Elemente (Götternamen)"))
    report.append(generate_markdown_table(Counter(starts), "Bevorzugte Anlaute"))
    report.append(generate_markdown_table(Counter(ends), "Bevorzugte Auslaute"))
    report.append(generate_markdown_table(cluster_counts, "Top Konsonanten-Cluster"))
    report.append(generate_markdown_table(cluster_type_data, "Struktur der Lautklassen-Cluster"))
    report.append(generate_markdown_table(sonority_stats, "Sonoritäts-Profil (Cluster-Tendenz)"))
    report.append(generate_markdown_table(Counter(cv_structures), "Top Silbenstrukturen (CV-Muster)"))
    report.append(generate_markdown_table(Counter(morpheme_roots), "Häufigste Morphem-Wurzeln (Top 15)"))
    report.append(generate_markdown_table(Counter(morpheme_suffixes), "Häufigste Suffixe (Automatisch erkannt)"))
    report.append(generate_markdown_table(consonant_counts, "Rekonstruiertes Konsonanten-Inventar"))
    report.append(generate_markdown_table(vowel_counts, "Vokal-Inventar"))
    report.append(generate_markdown_table(Counter({k: v for k, v in bigrams.most_common(20)}), "Top Bigramme (Phonotaktik)"))
    report.append(generate_markdown_table(Counter({f"{k} Zeichen": v for k, v in length_dist.items()}), "Namenslängen-Verteilung"))
    report.append(generate_markdown_table(Counter({f"{k} Silbe(n)": v for k, v in syllable_dist.items()}), "Silbenanzahl-Verteilung"))

    # Vowel position table
    report.append("\n### Vokalposition (anlautend / medial / auslautend)")
    report.append("| Vokal | Anlaut | Medial | Auslaut |")
    report.append("| :---: | ---: | ---: | ---: |")
    all_vowels = sorted(set(list(v_initial) + list(v_medial) + list(v_final)))
    for v in all_vowels:
        report.append(f"| **{v}** | {v_initial.get(v, 0)} | {v_medial.get(v, 0)} | {v_final.get(v, 0)} |")

    # Theophoric productivity
    report.append("\n### Theophore Produktivität (Götter × einzigartige Stämme)")
    report.append("| Gottheit | Einzigartige Stämme |")
    report.append("| :--- | ---: |")
    for god, count in sorted(god_productivity.items(), key=lambda x: -x[1]):
        report.append(f"| {god} | {count} |")

    # Consonantal skeleton variants
    report.append(f"\n### Konsonantenskelett-Varianten ({len(skeleton_variants)} Gruppen mit ≥2 Belegen)")
    report.append("| Skelett | Namensvarianten |")
    report.append("| :--- | :--- |")
    for skel, names_list in sorted(skeleton_variants.items(), key=lambda x: -len(x[1]))[:20]:
        report.append(f"| `{skel}` | {', '.join(names_list)} |")

    # Minimal pairs
    report.append(f"\n### Minimale Paare ({len(minimal_pairs)} Paare, Hamming-Distanz 1)")
    report.append("| Name A | Name B | Position |")
    report.append("| :--- | :--- | :---: |")
    for a, b in minimal_pairs[:30]:
        diff_pos = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
        report.append(f"| {a} | {b} | {diff_pos + 1} (`{a[diff_pos]}`→`{b[diff_pos]}`) |")

    report.append("\n## Vertiefende Suffix-Analyse: Wurzel-Kombinationen")
    report.append("| Suffix | Anzahl Belege | Beispiel-Wurzeln (Kollokationen) |")
    report.append("| :--- | :---: | :--- |")
    sorted_suffixes = sorted(Counter(morpheme_suffixes).items(), key=lambda x: x[1], reverse=True)
    for suff, count in sorted_suffixes[:20]:
        roots_list = ", ".join(suffix_to_roots.get(suff, [])[:5]) 
        report.append(f"| **-{suff}** | {count} | {roots_list} ... |")

    
    report.append("\n## Root Productivity: Most Versatile Morphemes")
    report.append("| Root | Unique Suffixes | Suffix List |")
    report.append("| :--- | :---: | :--- |")
    sorted_roots = sorted(root_productivity.items(), key=lambda x: x[1], reverse=True)
    for root, count in sorted_roots[:15]:
        suffixes_found = ", ".join(root_to_suffixes[root])
        report.append(f"| **{root}** | {count} | {suffixes_found} |")

    # LLM-enriched analysis sections
    if llm_enriched > 0:
        report.append(generate_markdown_table(
            dict(llm_semantic_fields),
            "Semantische Felder (LLM-Analyse)"
        ))
        report.append(generate_markdown_table(
            dict(llm_confidence),
            "Konfidenz der LLM-Etymologien"
        ))

        # Sample: show notable etymological hypotheses (high/medium confidence)
        notable = [
            e for e in llm_entries
            if e["llm_analysis"].get("confidence") in ("high", "medium")
        ][:15]
        if notable:
            report.append("\n## Ausgewählte Etymologie-Hypothesen (LLM, Konfidenz: medium/high)")
            report.append("| Name | Semantisches Feld | Hypothese |")
            report.append("| :--- | :--- | :--- |")
            for e in notable:
                la = e["llm_analysis"]
                hyp = la.get("etymology_hypothesis", "")[:80].replace("|", "/")
                report.append(
                    f"| **{e['transcription']}** "
                    f"| {la.get('semantic_field', '')[:30]} "
                    f"| {hyp}... |"
                )

        # Embed corpus synthesis if available
        synthesis_path = "output/corpus_synthesis.md"
        if os.path.exists(synthesis_path):
            report.append("\n---\n")
            report.append("## Korpus-Synthese (Claude Opus)\n")
            with open(synthesis_path, "r", encoding="utf-8") as f:
                # Skip the header lines already in the synthesis file
                lines = f.readlines()
                report.append("".join(lines[4:]))  # skip title + metadata lines

    os.makedirs("output", exist_ok=True)
    with open("output/phonetik_tabelle.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("\n[INFO] Der tabellarische Bericht wurde in 'output/phonetik_tabelle.md' gespeichert.")