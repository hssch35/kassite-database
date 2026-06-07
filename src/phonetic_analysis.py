"""
src/phonetic_analysis.py

NLP-based phonetic analysis for cross-language cognate detection.

Techniques:
  - Weighted edit distance adapted for cuneiform transliteration phonemes
  - Consonantal skeleton alignment
  - Automatic cognate candidate scoring (Kassitisch ↔ Hurrian ↔ Sanskrit)
  - Hierarchical clustering of name groups by phonetic similarity
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Generator

import numpy as np
from sklearn.cluster import AgglomerativeClustering

# ── Phoneme classes for weighted distance ────────────────────────────────────

# Phones that are acoustically close cost less to substitute.
# Organised by natural class; members share ≥ 2 features.
_NATURAL_CLASSES: list[frozenset[str]] = [
    frozenset(["b", "p", "m"]),          # labials
    frozenset(["d", "t", "n"]),          # dentals / alveolars
    frozenset(["g", "k", "ŋ"]),          # velars
    frozenset(["s", "z", "š", "ṣ"]),    # sibilants
    frozenset(["r", "l"]),               # liquids
    frozenset(["ḫ", "h", "x"]),          # laryngeals / fricatives
    frozenset(["a", "ā", "â"]),          # low vowels
    frozenset(["i", "ī", "e", "ē"]),    # front vowels
    frozenset(["u", "ū", "o", "ō"]),    # back/round vowels
]

VOWELS = set("aeiouāīūêâîûàèìò")
CONSONANTS_TO_SKIP = set()  # reserved for language-specific adjustments


def phoneme_substitution_cost(a: str, b: str) -> float:
    """Cost to substitute phoneme a with phoneme b (0 = identical, 1 = unrelated)."""
    if a == b:
        return 0.0
    # both in same natural class → cheap substitution
    for cls in _NATURAL_CLASSES:
        if a in cls and b in cls:
            return 0.3
    # vowel ↔ vowel across classes
    if a in VOWELS and b in VOWELS:
        return 0.5
    # consonant ↔ consonant across classes
    if a not in VOWELS and b not in VOWELS:
        return 0.7
    # consonant ↔ vowel
    return 1.0


# ── Tokeniser ─────────────────────────────────────────────────────────────────

# Multi-character digraphs / special chars that count as single phonemes
_DIGRAPHS = ["aš", "aḫ", "āš", "āḫ", "uš", "ur", "ir", "ar", "an", "am",
             "ḫu", "ḫa", "ḫi", "šu", "ša", "ši", "ṣu", "ṣa", "ṣi",
             "ts", "dz", "th", "ph", "kh", "nd", "mb", "ng", "nt", "rt",
             "rb", "rd", "rn", "lt", "ld", "lk", "st", "sk", "sp"]
_DIGRAPH_RE = re.compile(
    "(" + "|".join(re.escape(d) for d in sorted(_DIGRAPHS, key=len, reverse=True)) + "|.)",
    re.DOTALL,
)


def tokenize(name: str) -> list[str]:
    """Split a transliterated name into phoneme tokens."""
    clean = name.lower().strip()
    clean = re.sub(r"[\s\-/\(\)\[\]?!0]", "", clean)
    return _DIGRAPH_RE.findall(clean)


# ── Weighted edit distance ────────────────────────────────────────────────────

def phonetic_distance(a: str, b: str,
                      gap_open: float = 0.5,
                      gap_extend: float = 0.2) -> float:
    """
    Needleman-Wunsch style distance between two transliterated names.
    Returns a value in [0, max_len] — normalise by dividing by max(len_a, len_b).
    """
    ta, tb = tokenize(a), tokenize(b)
    m, n = len(ta), len(tb)
    if m == 0 and n == 0:
        return 0.0
    if m == 0:
        return n * gap_open
    if n == 0:
        return m * gap_open

    # DP table
    dp = np.zeros((m + 1, n + 1), dtype=float)
    dp[0, :] = np.arange(n + 1) * gap_open
    dp[:, 0] = np.arange(m + 1) * gap_open

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sub   = dp[i-1, j-1] + phoneme_substitution_cost(ta[i-1], tb[j-1])
            del_a = dp[i-1, j]   + gap_open
            del_b = dp[i, j-1]   + gap_open
            dp[i, j] = min(sub, del_a, del_b)

    raw = dp[m, n]
    return raw / max(m, n)   # normalised to [0, 1]


def consonant_skeleton(name: str) -> str:
    """Strip vowels → bare consonantal skeleton."""
    return "".join(c for c in tokenize(name) if c not in VOWELS)


# ── Cognate scoring ───────────────────────────────────────────────────────────

@dataclass
class CognateCandidate:
    name_a: str
    lang_a: str
    name_b: str
    lang_b: str
    phonetic_dist: float          # 0 = identical, 1 = unrelated
    skeleton_dist: float          # same but consonants only
    score: float                  # combined similarity (1 = perfect)
    notes: str = ""

    @property
    def similarity(self) -> float:
        return round(1.0 - self.score, 4)


def _combined_score(pd_: float, sd: float,
                    w_phonetic: float = 0.6, w_skeleton: float = 0.4) -> float:
    return w_phonetic * pd_ + w_skeleton * sd


def find_cognate_candidates(
    names_a: list[tuple[str, str]],   # [(name, language), ...]
    names_b: list[tuple[str, str]],
    threshold: float = 0.45,          # max score to count as candidate
) -> list[CognateCandidate]:
    """
    Compare two name lists cross-linguistically, return candidates
    with combined score ≤ threshold (lower = more similar).
    """
    candidates: list[CognateCandidate] = []
    for (na, la), (nb, lb) in ((a, b) for a in names_a for b in names_b):
        if na == nb:
            continue
        pd_  = phonetic_distance(na, nb)
        sd   = phonetic_distance(consonant_skeleton(na), consonant_skeleton(nb))
        sc   = _combined_score(pd_, sd)
        if sc <= threshold:
            candidates.append(CognateCandidate(na, la, nb, lb, pd_, sd, sc))

    candidates.sort(key=lambda x: x.score)
    return candidates


# ── Cross-corpus comparison from SQLite ──────────────────────────────────────

def load_corpus_names(db_path: str, corpus_name: str) -> list[tuple[str, str]]:
    """Load (transcription, language_iso) pairs for a corpus from the DB."""
    con = sqlite3.connect(db_path)
    rows = con.execute("""
        SELECT n.transcription, l.iso_code
        FROM names n
        JOIN corpora c ON n.corpus_id = c.id
        JOIN languages l ON c.language_id = l.id
        WHERE c.name = ?
    """, (corpus_name,)).fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]


def run_cross_corpus_cognate_search(
    db_path: str,
    corpus_a: str,
    corpus_b: str,
    threshold: float = 0.40,
) -> list[CognateCandidate]:
    """
    Load two corpora from the DB and return all cognate candidates.
    """
    names_a = load_corpus_names(db_path, corpus_a)
    names_b = load_corpus_names(db_path, corpus_b)
    if not names_a or not names_b:
        return []
    return find_cognate_candidates(names_a, names_b, threshold)


# ── Morpheme element alignment ────────────────────────────────────────────────

def align_morpheme_elements(
    elements_a: list[str],
    elements_b: list[str],
    threshold: float = 0.35,
) -> list[tuple[str, str, float]]:
    """
    Given two lists of name elements (roots, suffixes, theophoric components),
    find the closest matches between them.
    Returns list of (elem_a, elem_b, distance).
    """
    matches = []
    for ea in elements_a:
        best_dist = 1.0
        best_eb   = None
        for eb in elements_b:
            d = phonetic_distance(ea, eb)
            if d < best_dist:
                best_dist, best_eb = d, eb
        if best_eb and best_dist <= threshold:
            matches.append((ea, best_eb, best_dist))
    return sorted(matches, key=lambda x: x[2])


# ── Clustering ────────────────────────────────────────────────────────────────

@dataclass
class PhoneticCluster:
    cluster_id: int
    members: list[str]
    centroid_name: str   # member closest to mean pairwise distance


def cluster_names(
    names: list[str],
    n_clusters: int | None = None,
    distance_threshold: float = 0.35,
) -> list[PhoneticCluster]:
    """
    Agglomerative clustering of names by phonetic distance.
    If n_clusters is None, uses distance_threshold to auto-cut.
    Returns list of PhoneticCluster objects.
    """
    if len(names) < 2:
        return [PhoneticCluster(0, names, names[0] if names else "")]

    # Build full distance matrix
    n = len(names)
    dist_matrix = np.zeros((n, n))
    for i, j in combinations(range(n), 2):
        d = phonetic_distance(names[i], names[j])
        dist_matrix[i, j] = d
        dist_matrix[j, i] = d

    kwargs: dict = dict(metric="precomputed", linkage="average")
    if n_clusters:
        kwargs["n_clusters"] = n_clusters
    else:
        kwargs["n_clusters"] = None
        kwargs["distance_threshold"] = distance_threshold

    model = AgglomerativeClustering(**kwargs)
    labels = model.fit_predict(dist_matrix)

    clusters: dict[int, list[int]] = defaultdict(list)
    for idx, lbl in enumerate(labels):
        clusters[int(lbl)].append(idx)

    result = []
    for cid, idxs in sorted(clusters.items()):
        members = [names[i] for i in idxs]
        # centroid = member with lowest mean distance to all others in cluster
        sub = dist_matrix[np.ix_(idxs, idxs)]
        mean_dists = sub.mean(axis=1)
        centroid_idx = idxs[int(np.argmin(mean_dists))]
        result.append(PhoneticCluster(cid, members, names[centroid_idx]))

    return result


# ── Morpheme similarity search ────────────────────────────────────────────────

def find_similar_morphemes(
    query: str,
    morpheme_list: list[str],
    top_n: int = 10,
    threshold: float = 0.5,
) -> list[tuple[str, float]]:
    """Find morphemes phonetically closest to query."""
    scored = [
        (m, phonetic_distance(query, m))
        for m in morpheme_list
        if m != query
    ]
    scored = [(m, d) for m, d in scored if d <= threshold]
    scored.sort(key=lambda x: x[1])
    return scored[:top_n]
