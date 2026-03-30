# FOA Ingestion + Semantic Tagging
**HumanAI GSoC 2026 — Screening Task**  
*AI-Powered Funding Intelligence*

---

## What This Does

A command-line tool that:
1. **Fetches** a Funding Opportunity Announcement (FOA) from Grants.gov or NSF
2. **Extracts** structured fields (title, agency, dates, award range, description, eligibility)
3. **Tags** the FOA semantically using a rule-based ontology (research domain, methods, populations, sponsor themes)
4. **Exports** results as `foa.json` and `foa.csv`

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py --url "<FOA_URL>" --out_dir ./out
```

### Examples

```bash
# Grants.gov
python main.py --url "https://grants.gov/search-results-detail/354817" --out_dir ./out

# NSF
python main.py --url "https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=505819" --out_dir ./out
```

---

## Output

```
out/
├── foa.json   ← full structured record with semantic tags
└── foa.csv    ← flat tabular version, tags as pipe-separated strings
```

### foa.json structure

```json
{
  "foa_id": "NSF-505819",
  "title": "...",
  "agency": "National Science Foundation (NSF)",
  "open_date": "2025-01-01",
  "close_date": "2025-06-30",
  "award_range": "N/A",
  "description": "...",
  "eligibility": "...",
  "source_url": "https://...",
  "semantic_tags": {
    "research_domains": ["computer_science", "social_science"],
    "methods": ["machine_learning", "modeling"],
    "populations": ["underserved"],
    "sponsor_themes": ["applied_research"]
  },
  "ingested_at": "2026-03-29T18:00:00Z"
}
```

---

## Semantic Tagging Ontology

Tags are applied via **keyword matching** across 4 categories:

| Category | Labels |
|---|---|
| `research_domains` | biomedical, computer_science, environment, social_science, engineering, physics |
| `methods` | machine_learning, clinical_trial, survey, modeling |
| `populations` | youth, elderly, underserved, general_public | 
| `sponsor_themes` | basic_research, applied_research, workforce, infrastructure |


---

## Project Structure

```
foa_tool/
├── main.py            ← main script
├── requirements.txt   ← dependencies
├── README.md          ← this file
└── out/
    ├── foa.json
    └── foa.csv
```

---

## Design Decisions

- **Modular parsers**: Grants.gov and NSF each have their own parsing logic, with a generic HTML fallback for other sources
- **Rule-based tagging**: Deterministic, reproducible, and transparent — no black-box models needed for the screening task
- **Graceful fallbacks**: If a field can't be extracted, it defaults to `"N/A"` rather than crashing
- **Extensible ontology**: The `ONTOLOGY` dict in `main.py` can be expanded with new categories and keywords easily

---

## Future Extensions (Full GSoC Project)

- Add NIH, DOE, DARPA as additional sources
- Replace rule-based tags with `sentence-transformers` embedding similarity
- Add FAISS/Chroma vector index for semantic search
- Build a lightweight CLI search interface
- LLM-assisted classification as stretch goal
