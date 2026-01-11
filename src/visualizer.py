# src/visualizer.py
import matplotlib.pyplot as plt
from collections import Counter

def plot_god_distribution(theophoric_names):
    """
    Erstellt ein Balkendiagramm basierend auf den gefundenen Götternamen.
    """
    all_found_gods = []
    for item in theophoric_names:
        all_found_gods.extend(item['gods']) 

    god_counts = Counter(all_found_gods)
    common_gods = god_counts.most_common()

    names = [x[0] for x in common_gods] 
    counts = [x[1] for x in common_gods]

    plt.figure(figsize=(10, 6))
    plt.bar(names, counts, color='skyblue', edgecolor='navy')
    plt.title('Häufigkeit der Gottheiten in den kassitischen Namen', fontsize=14)
    plt.xlabel('Gottheit', fontsize=12)
    plt.ylabel('Anzahl der Nennungen', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    for i, v in enumerate(counts):
        plt.text(i, v + 0.2, str(v), ha='center', fontweight='bold')

    plt.tight_layout()
    # Wichtig: In Skripten brauchen wir plt.show(), damit das Fenster aufpoppt
    plt.show()
    
import matplotlib.pyplot as plt

def plot_phonetic_distribution(counts, title, filename):
    """Erstellt ein Balkendiagramm für Lautklassen."""
    labels = list(counts.keys())
    values = list(counts.values())

    plt.figure(figsize=(10, 6))
    plt.bar(labels, values, color='skyblue', edgecolor='navy')
    plt.title(title)
    plt.ylabel('Häufigkeit')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig(f"output/{filename}.png")
    plt.close()

def plot_vowel_correlation(correlation_counts, filename):
    """Visualisiert die Wurzel-Suffix-Vokal-Muster."""
    
    top_patterns = dict(correlation_counts.most_common(8))
    
    plt.figure(figsize=(12, 6))
    plt.bar(top_patterns.keys(), top_patterns.values(), color='salmon')
    plt.title('Vokal-Korrelation (Wurzel -> Suffix)')
    plt.xlabel('Muster (Wurzelvokal -> Suffix)')
    plt.ylabel('Anzahl')
    
    plt.savefig(f"output/{filename}.png")
    plt.close()