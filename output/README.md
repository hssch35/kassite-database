# Kassite Onomastics: Digital Morpheme Analysis

This project utilizes Python to statistically investigate the structure of Kassite personal names. It focuses on the automatic identification of suffixes, roots, and phonological patterns within the Kassite language.

## Methodology
- **Suffix Discovery:** Statistical scanning of word endings (length 2-4) across the dataset to identify candidates for affixes.
- **Morphemic Segmentation:** Automatic splitting of names into roots and suffixes using a "Longest Match" algorithm.
- **Collocation Matrix:** Mapping roots to specific suffixes to identify grammatical productivity and theophoric patterns.

## Key Findings (Morpheme Analysis)
| Suffix | Count | Type / Description |
| :--- | :--- | :--- |
| **-saḫ** | 61 | Theophoric element (god *Saḫ*) |
| **-iaš** | 22 | Grammatical suffix / Determinative |
| **-šiḫu** | 12 | Theophoric element (God *Marduk*) |

## Project Structure
- `main.py`: Orchestrates data enrichment and statistical processing.
- `src/linguistics.py`: Core library for phonetic analysis, CV-patterns, and morphology.
- `generate_report.py`: Generates the comprehensive linguistic report in Markdown.
- `output/`: Contains generated analysis results and tables.

## How to Run
1. Ensure your data is in `data/kassite_names_db.json`.
2. Run `python main.py` to process the data.
3. Run `python generate_report.py` to view results in the `output/` folder.

