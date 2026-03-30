"""
FOA Ingestion + Semantic Tagging
HumanAI GSoC 2026 - Screening Task
"""

import argparse
import json
import csv
import re
import uuid
import os
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# ______________________________________________
# ONTOLOGY: Rule-based semantic tagging
# ____________________________________________________________

ONTOLOGY = {
    "research_domains": {
        "biomedical":        ["health", "medical", "clinical", "disease", "biomedical", "cancer", "drug", "patient"],
        "computer_science":  ["machine learning", "artificial intelligence", "ai", "software", "computing", "algorithm", "data science"],
        "environment":       ["climate", "environment", "ecology", "sustainability", "energy", "water", "pollution"],
        "social_science":    ["social", "community", "education", "policy", "equity", "justice", "mental health"],
        "engineering":       ["engineering", "infrastructure", "manufacturing", "materials", "robotics"],
        "physics":           ["physics", "quantum", "nuclear", "particle", "optics", "photonics"],
    },
    "methods": {
        "machine_learning":  ["machine learning", "deep learning", "neural network", "nlp", "computer vision"],
        "clinical_trial":    ["clinical trial", "randomized", "placebo", "intervention"],
        "survey":            ["survey", "questionnaire", "interview", "qualitative"],
        "modeling":          ["model", "simulation", "computational", "mathematical"],
    },
    "populations": {
        "youth":             ["youth", "children", "adolescent", "student", "k-12"],
        "elderly":           ["elderly", "aging", "older adult", "senior"],
        "underserved":       ["underserved", "underrepresented", "minority", "low-income", "rural"],
        "general_public":    ["general public", "community", "population"],
    },
    "sponsor_themes": {
        "basic_research":    ["fundamental", "basic research", "discovery", "exploratory"],
        "applied_research":  ["applied", "translational", "implementation", "practical"],
        "workforce":         ["workforce", "training", "fellowship", "career", "graduate"],
        "infrastructure":    ["infrastructure", "facility", "equipment", "center"],
    },
}


def apply_tags(text: str) -> dict:
    text_lower = text.lower()
    tags = {}
    for category, labels in ONTOLOGY.items():
        matched = []
        for label, keywords in labels.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(label)
        tags[category] = matched if matched else ["unclassified"] #prototype exception
    return tags



def parse_grants_gov(url: str, soup: BeautifulSoup) -> dict:

    def get_text(selector, attr=None):
        el = soup.select_one(selector)
        if not el:
            return None
        return el.get(attr) if attr else el.get_text(strip=True)

    # Try to get opportunity number sous la forme FOA id
    foa_id = None
    for label in soup.find_all(string=re.compile(r"Opportunity Number", re.I)):
        parent = label.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                foa_id = sibling.get_text(strip=True)
                break

    # Title
    title = None
    for tag in ["h1", "h2", ".opportunity-title", "#opportunityTitle"]:
        el = soup.select_one(tag)
        if el:
            title = el.get_text(strip=True)
            break

    # Agency
    agency = None
    for label in soup.find_all(string=re.compile(r"Agency Name|Grantor", re.I)):
        parent = label.find_parent()
        if parent:
            sibling = parent.find_next_sibling()
            if sibling:
                agency = sibling.get_text(strip=True)
                break

    # Dates
    open_date, close_date = None, None
    for label in soup.find_all(string=re.compile(r"Posted Date|Open Date", re.I)):
        parent = label.find_parent()
        if parent:
            sib = parent.find_next_sibling()
            if sib:
                open_date = sib.get_text(strip=True)
    for label in soup.find_all(string=re.compile(r"Close Date|Deadline|Due Date", re.I)):
        parent = label.find_parent()
        if parent:
            sib = parent.find_next_sibling()
            if sib:
                close_date = sib.get_text(strip=True)

    # Award range
    award = None
    for label in soup.find_all(string=re.compile(r"Award Ceiling|Award Floor|Funding", re.I)):
        parent = label.find_parent()
        if parent:
            sib = parent.find_next_sibling()
            if sib:
                award = sib.get_text(strip=True)
                break

    # Description _ just grab everything descriptive
    description = ""
    for tag in soup.find_all(["p", "div", "section"]):
        txt = tag.get_text(strip=True)
        if len(txt) > 100:
            description = txt[:2000]
            break

    eligibility = None
    for label in soup.find_all(string=re.compile(r"Eligible Applicants|Eligibility", re.I)):
        parent = label.find_parent()
        if parent:
            sib = parent.find_next_sibling()
            if sib:
                eligibility = sib.get_text(strip=True)[:500]
                break

    return {
        "foa_id":       foa_id or str(uuid.uuid4())[:8].upper(),
        "title":        title or "N/A",
        "agency":       agency or "N/A",
        "open_date":    open_date or "N/A",
        "close_date":   close_date or "N/A",
        "award_range":  award or "N/A",
        "description":  description or "N/A",
        "eligibility":  eligibility or "N/A",
        "source_url":   url,
    }



def parse_nsf(url: str) -> dict:
    # Try to extract program ID from URL
    match = re.search(r'programid=(\d+)', url, re.I) or re.search(r'/(\d{6,})', url)
    if match:
        program_id = match.group(1)
        api_url = f"https://www.nsf.gov/funding/pgm_summ.jsp?pims_id={program_id}&from=fund"
        try:
            resp = requests.get(api_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.select_one("h1, h2, .programTitle")
            title = title_el.get_text(strip=True) if title_el else "N/A"

            desc_el = soup.find("div", {"id": "pgm_desc"}) or soup.find("div", class_=re.compile("desc|summary", re.I))
            description = desc_el.get_text(strip=True)[:2000] if desc_el else "N/A"

            return {
                "foa_id":      f"NSF-{program_id}",
                "title":       title,
                "agency":      "National Science Foundation (NSF)",
                "open_date":   "N/A",
                "close_date":  "N/A",
                "award_range": "N/A",
                "description": description,
                "eligibility": "N/A",
                "source_url":  url,
            }
        except Exception:
            pass

    # Generic HTML fallback
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    return parse_grants_gov(url, soup)


def ingest(url: str) -> dict:
    """Fetch and parse an FOA from a given URL."""
    print(f"[→] Fetching: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FOA-Bot/1.0)"}

    try:
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(f"[✗] Failed to fetch URL: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")
    domain = urlparse(url).netloc.lower()

    if "nsf.gov" in domain:
        foa = parse_nsf(url)
    else:
        foa = parse_grants_gov(url, soup)

    # Apply semantic tags
    combined_text = f"{foa.get('title','')} {foa.get('description','')} {foa.get('eligibility','')}"
    foa["semantic_tags"] = apply_tags(combined_text)
    foa["ingested_at"] = datetime.utcnow().isoformat() + "Z"

    print(f"[✓] Parsed: {foa['title']}")
    return foa




def export(foa: dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    # JSON form
    json_path = os.path.join(out_dir, "foa.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(foa, f, indent=2, ensure_ascii=False)
    print(f"[✓] Saved JSON → {json_path}")

    csv_path = os.path.join(out_dir, "foa.csv")
    flat = {k: v for k, v in foa.items() if k != "semantic_tags"}
    tags = foa.get("semantic_tags", {})
    for cat, vals in tags.items():
        flat[f"tag_{cat}"] = "|".join(vals)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        writer.writeheader()
        writer.writerow(flat)
    print(f"[✓] Saved CSV  → {csv_path}")


#______________________________________main____________________________________________________________________________
parser = argparse.ArgumentParser(
    description="FOA Ingestion + Semantic Tagging — HumanAI GSoC 2026"
)
parser.add_argument("--url",     required=True, help="URL of the FOA to ingest")
parser.add_argument("--out_dir", default="./out", help="Output directory (default: ./out)")
args = parser.parse_args()

foa = ingest(args.url)
export(foa, args.out_dir)
print("\n[✓] Done!")
#________________________________________________________________________________________________



