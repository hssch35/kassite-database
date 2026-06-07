"""
LLM-powered linguistic analysis for Kassite onomastics using the Claude API.

Uses claude-haiku-4-5 for per-name enrichment (cost-efficient at scale)
and claude-opus-4-6 with adaptive thinking for the holistic corpus synthesis.
"""

import json
import anthropic
from pydantic import BaseModel


KASSITE_SYSTEM_PROMPT = """You are a specialist in ancient Near Eastern linguistics, \
focusing on Kassite onomastics — the study of personal names from the Kassite dynasty \
of ancient Mesopotamia (c. 1600–1155 BCE).

Key facts about the Kassite language:
- Language isolate: no confirmed relatives; extremely poorly attested (~30–40 known words)
- Names are often theophoric compounds: divine element + personal stem
- Known divine names: Bugaš/Šugab, Šuriaš (sun god), Maruttaš, Buriaš (storm god),
  Indaš, Ḫarbe (syncretised with Enlil), Ḫala, Saḫ
- Productive suffixes: -aš, -iaš, -ak; vocalic endings -i, -a, -u
- Comparable traditions: Hurrian (e.g. -šarri "king", -tilla "hero/life"),
  Akkadian loanwords and naming conventions, Elamite parallels

When forming etymological hypotheses, clearly flag uncertainty with phrases like
"possibly", "may reflect", "cf.", or "tentatively". Do not overstate certainty."""


class NameAnalysis(BaseModel):
    etymology_hypothesis: str   # proposed etymology with explicit uncertainty markers
    semantic_field: str         # e.g. "divine protection", "natural force", "royal epithet"
    linguistic_notes: str       # phonological or morphological observations
    comparable_forms: str       # analogues in Hurrian, Akkadian, Elamite, etc.
    confidence: str             # "low" | "medium" | "high"


def _build_name_prompt(entry: dict) -> str:
    parts = [f"Name: {entry.get('transcription', '')}"]
    if entry.get('structure'):
        parts.append(f"CV structure: {entry['structure']}")
    if entry.get('morpheme_root'):
        parts.append(f"Morpheme root: {entry['morpheme_root']}")
    if entry.get('morpheme_suffix'):
        parts.append(f"Morpheme suffix: {entry['morpheme_suffix']}")
    if entry.get('isolated_stem'):
        parts.append(f"Isolated stem: {entry['isolated_stem']}")
    if entry.get('detected_gods'):
        parts.append(f"Theophoric elements: {', '.join(entry['detected_gods'])}")
    if entry.get('meaning'):
        parts.append(f"Attested meaning: {entry['meaning']}")
    if entry.get('morphemes'):
        parts.append(f"Traditional morpheme segmentation: {entry['morphemes']}")
    parts.append("\nProvide a concise linguistic analysis of this Kassite personal name.")
    return "\n".join(parts)


def analyze_name(client: anthropic.Anthropic, entry: dict) -> NameAnalysis:
    """
    Analyze a single Kassite DB entry and return structured linguistic insights.
    Uses claude-haiku-4-5 with prompt caching on the system prompt.
    """
    response = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=600,
        system=[{
            "type": "text",
            "text": KASSITE_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": _build_name_prompt(entry)}],
        output_format=NameAnalysis,
    )
    return response.parsed_output


def generate_corpus_synthesis(client: anthropic.Anthropic, stats: dict) -> str:
    """
    Generate a holistic scholarly synthesis of the corpus.
    Uses claude-opus-4-6 with adaptive thinking and streaming.
    """
    prompt = f"""You are writing a synthesis section for a scholarly monograph on \
Kassite onomastics. The corpus comprises {stats.get('total', 0)} attested personal \
names from Kassite-period Mesopotamia.

Statistical summary of the corpus:
{json.dumps(stats, ensure_ascii=False, indent=2)}

Write 6–7 paragraphs of rigorous scholarly prose addressing:

1. **Phoneme inventory** — what consonants and vowels can be reconstructed from the \
corpus; distribution of consonant classes (labials, dentals, velars, sibilants, \
liquids, nasals); what may be absent or marginal.

2. **Phonotactics** — the top bigrams reveal which sound sequences are preferred or \
avoided; consonant cluster types and their sonority profiles; syllable templates.

3. **Morphological analysis** — productive suffixes and their probable functions, \
root types, evidence for compounding vs. simplex names; name-length and syllable-count \
distributions and what they imply for word structure.

4. **Vowel patterning** — positional vowel frequencies (initial / medial / final); \
evidence for or against vowel harmony; the role of vowels in suffixation.

5. **Theophoric elements and religion** — which deities appear most frequently, \
theophoric productivity (how many unique stems each god forms names with), and what \
this suggests about the Kassite pantheon and its relation to Babylonian religion.

6. **Variant detection and minimal pairs** — consonantal skeleton groups and minimal \
pairs as evidence for phonemic contrasts, scribal conventions, and dialectal variation.

7. **Contact and sociolinguistic implications** — similarities with Hurrian, Akkadian, \
and Elamite naming conventions; evidence for language contact, scribal assimilation, \
and what the corpus reveals about Kassite identity.

Maintain scholarly rigour and acknowledge the highly speculative nature of interpretations \
where Kassite is concerned. Use hedged language accordingly."""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=KASSITE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final = stream.get_final_message()

    return next(
        (block.text for block in final.content if block.type == "text"), ""
    )


def build_corpus_stats(db: list) -> dict:
    """Aggregate corpus statistics for use in the synthesis prompt."""
    from collections import Counter

    starts, ends, suffixes, gods, cv_structures = [], [], [], [], []
    semantic_fields, confidence_levels = [], []

    for e in db:
        root = e.get("morpheme_root") or e.get("root") or ""
        if root and root not in ["Unbekannt"] and len(root) >= 2:
            starts.append(root[0].upper())
            ends.append(root[-1].lower())
        if e.get("morpheme_suffix"):
            suffixes.append(e["morpheme_suffix"].lower())
        for g in e.get("detected_gods", []):
            gods.append(g)
        if e.get("structure"):
            cv_structures.append(e["structure"])
        if e.get("llm_analysis"):
            la = e["llm_analysis"]
            if la.get("semantic_field"):
                semantic_fields.append(la["semantic_field"])
            if la.get("confidence"):
                confidence_levels.append(la["confidence"])

    from src.linguistics import (
        analyze_phoneme_inventory, analyze_bigrams,
        analyze_syllable_distribution, analyze_name_length,
        detect_consonantal_skeleton_variants, find_minimal_pairs,
    )
    all_names = [e.get("transcription") for e in db if e.get("transcription")]
    consonants, vowels = analyze_phoneme_inventory(all_names)
    bigrams = analyze_bigrams(all_names)
    syllable_dist = analyze_syllable_distribution(all_names)
    length_dist = analyze_name_length(all_names)
    variants = detect_consonantal_skeleton_variants(all_names)
    pairs = find_minimal_pairs(all_names)

    return {
        "total": len(db),
        "top_initial_consonants": dict(Counter(starts).most_common(10)),
        "top_final_consonants": dict(Counter(ends).most_common(10)),
        "top_suffixes": dict(Counter(suffixes).most_common(15)),
        "top_theophoric_elements": dict(Counter(gods).most_common(10)),
        "top_cv_structures": dict(Counter(cv_structures).most_common(10)),
        "entries_with_attested_meaning": sum(1 for e in db if e.get("meaning")),
        "entries_with_theophoric_element": sum(1 for e in db if e.get("detected_gods")),
        "entries_llm_enriched": sum(1 for e in db if e.get("llm_analysis")),
        "semantic_field_distribution": dict(Counter(semantic_fields).most_common(12)),
        "llm_confidence_distribution": dict(Counter(confidence_levels).most_common()),
        # new
        "phoneme_inventory_consonants": dict(consonants.most_common(20)),
        "phoneme_inventory_vowels": dict(vowels.most_common()),
        "top_bigrams": dict(bigrams.most_common(15)),
        "syllable_distribution": {str(k): v for k, v in syllable_dist.items()},
        "name_length_distribution": {str(k): v for k, v in length_dist.items()},
        "consonantal_skeleton_variant_groups": len(variants),
        "minimal_pair_count": len(pairs),
    }
