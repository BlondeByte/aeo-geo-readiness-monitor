from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

INPUT_FILE = Path("urls.csv")
OUTPUT_DIR = Path("output")
CSV_OUTPUT = OUTPUT_DIR / "aeo_audit.csv"
JSON_OUTPUT = OUTPUT_DIR / "aeo_audit.json"

HEADERS = {
    "User-Agent": "AEOAnswerReadinessAuditor/1.0 (educational structural analysis)"
}
TIMEOUT = 20

QUESTION_WORDS = (
    "who", "what", "when", "where", "why", "how", "can", "does", "do",
    "is", "are", "should", "which"
)

REFERENCE_TERMS = (
    "references", "sources", "resources", "citations", "further reading",
    "related resources"
)

DATE_KEYS = (
    "datepublished", "datemodified", "article:published_time",
    "article:modified_time", "last-modified", "date"
)


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def get_meta(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
        if not tag:
            tag = soup.find("meta", attrs={"property": re.compile(f"^{re.escape(name)}$", re.I)})
        if tag and tag.get("content"):
            return clean_text(tag.get("content"))
    return ""


def extract_schema_types(soup: BeautifulSoup) -> list[str]:
    types = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def walk(obj):
            if isinstance(obj, dict):
                t = obj.get("@type")
                if isinstance(t, str):
                    types.add(t)
                elif isinstance(t, list):
                    types.update(str(x) for x in t)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)
    return sorted(types)


def heading_question_count(headings: list[str]) -> int:
    total = 0
    for h in headings:
        normalized = h.strip().lower()
        first = normalized.split(" ", 1)[0] if normalized else ""
        if normalized.endswith("?") or first in QUESTION_WORDS:
            total += 1
    return total


def concise_answers_after_headings(soup: BeautifulSoup) -> int:
    count = 0
    for heading in soup.find_all(["h1", "h2", "h3"]):
        nxt = heading.find_next_sibling()
        while nxt and nxt.name in {"div", "section"} and not clean_text(nxt.get_text(" ", strip=True)):
            nxt = nxt.find_next_sibling()
        if nxt and nxt.name == "p":
            words = clean_text(nxt.get_text(" ", strip=True)).split()
            if 15 <= len(words) <= 80:
                count += 1
    return count


def count_reference_sections(headings: list[str]) -> int:
    count = 0
    for heading in headings:
        low = heading.lower()
        if any(term in low for term in REFERENCE_TERMS):
            count += 1
    return count


def link_counts(soup: BeautifulSoup, base_url: str) -> tuple[int, int]:
    base_domain = urlparse(base_url).netloc.lower()
    internal = 0
    outbound = 0
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.lower() == base_domain:
            internal += 1
        else:
            outbound += 1
    return internal, outbound


def date_hint(soup: BeautifulSoup) -> str:
    for key in DATE_KEYS:
        value = get_meta(soup, (key,))
        if value:
            return value
    time_tag = soup.find("time")
    if time_tag:
        return clean_text(time_tag.get("datetime") or time_tag.get_text(" ", strip=True))
    return ""


def score_row(row: dict) -> tuple[int, dict]:
    parts = {}

    parts["semantic_hierarchy"] = min(
        15,
        (5 if row["h1_count"] == 1 else 2 if row["h1_count"] > 0 else 0)
        + min(row["h2_count"], 5)
        + min(row["h3_count"], 5)
    )

    parts["answer_format"] = min(
        20,
        row["question_heading_count"] * 2
        + row["concise_answer_count"] * 2
    )

    parts["scannability"] = min(
        15,
        row["list_count"] * 2
        + row["table_count"] * 3
    )

    parts["structured_data"] = 15 if row["jsonld_present"] else 0
    if row["faq_schema"] or row["howto_schema"]:
        parts["structured_data"] = 15
    elif row["article_schema"] and parts["structured_data"] < 12:
        parts["structured_data"] = 12

    parts["metadata"] = (
        (4 if row["meta_description_present"] else 0)
        + (4 if row["canonical_present"] else 0)
        + (4 if row["date_hint_present"] else 0)
    )

    parts["source_signals"] = min(
        13,
        (5 if row["reference_section_count"] > 0 else 0)
        + min(row["outbound_link_count"], 8)
    )

    parts["readability"] = 10 if 25 <= row["avg_paragraph_words"] <= 90 else 5

    score = min(100, sum(parts.values()))
    return score, parts


def analyze(url: str, label: str, rights_basis: str, rights_page_url: str) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    meta_description = get_meta(soup, ("description",))

    headings_by_level = {}
    all_headings = []
    for level in ["h1", "h2", "h3"]:
        vals = [clean_text(x.get_text(" ", strip=True)) for x in soup.find_all(level)]
        vals = [x for x in vals if x]
        headings_by_level[level] = vals
        all_headings.extend(vals)

    paragraphs = [
        clean_text(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
    ]
    paragraphs = [p for p in paragraphs if p]
    paragraph_lengths = [len(p.split()) for p in paragraphs]
    avg_paragraph_words = round(
        sum(paragraph_lengths) / len(paragraph_lengths), 1
    ) if paragraph_lengths else 0

    page_text = clean_text(soup.get_text(" ", strip=True))
    word_count = len(page_text.split())

    schema_types = extract_schema_types(soup)
    schema_lower = {s.lower() for s in schema_types}
    internal_links, outbound_links = link_counts(soup, url)

    canonical = soup.find("link", rel=lambda x: x and "canonical" in [str(i).lower() for i in (x if isinstance(x, list) else [x])])
    date_value = date_hint(soup)

    row = {
        "label": label,
        "url": url,
        "rights_basis": rights_basis,
        "rights_page_url": rights_page_url,
        "http_status": response.status_code,
        "title": title,
        "meta_description_present": bool(meta_description),
        "h1_count": len(headings_by_level["h1"]),
        "h2_count": len(headings_by_level["h2"]),
        "h3_count": len(headings_by_level["h3"]),
        "question_heading_count": heading_question_count(all_headings),
        "concise_answer_count": concise_answers_after_headings(soup),
        "list_count": len(soup.find_all(["ul", "ol"])),
        "table_count": len(soup.find_all("table")),
        "word_count": word_count,
        "avg_paragraph_words": avg_paragraph_words,
        "internal_link_count": internal_links,
        "outbound_link_count": outbound_links,
        "reference_section_count": count_reference_sections(all_headings),
        "jsonld_present": bool(schema_types),
        "schema_types": ", ".join(schema_types),
        "faq_schema": "faqpage" in schema_lower,
        "howto_schema": "howto" in schema_lower,
        "article_schema": any(x in schema_lower for x in {"article", "newsarticle", "blogposting"}),
        "canonical_present": bool(canonical),
        "date_hint_present": bool(date_value),
        "date_hint": date_value,
    }

    score, parts = score_row(row)
    row["answer_readiness_score"] = score
    row["score_breakdown"] = json.dumps(parts, sort_keys=True)
    return row


def main():
    if not INPUT_FILE.exists():
        raise SystemExit(f"Missing input file: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE).fillna("")
    required = {"url", "label", "rights_basis", "rights_page_url", "human_approved"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"urls.csv is missing columns: {sorted(missing)}")

    approved = df[df["human_approved"].astype(str).str.upper().eq("YES")]

    if approved.empty:
        raise SystemExit(
            "No rows are approved. Verify rights manually, then set human_approved=YES "
            "for the pages you are allowed to analyze."
        )

    rows = []
    for _, r in approved.iterrows():
        url = str(r["url"]).strip()
        print(f"Analyzing: {url}")
        try:
            rows.append(
                analyze(
                    url=url,
                    label=str(r["label"]).strip(),
                    rights_basis=str(r["rights_basis"]).strip(),
                    rights_page_url=str(r["rights_page_url"]).strip(),
                )
            )
        except Exception as exc:
            rows.append({
                "label": str(r["label"]).strip(),
                "url": url,
                "rights_basis": str(r["rights_basis"]).strip(),
                "rights_page_url": str(r["rights_page_url"]).strip(),
                "error": f"{type(exc).__name__}: {exc}",
                "answer_readiness_score": 0,
            })
            print(f"  ERROR: {exc}")

    result = pd.DataFrame(rows)
    if "answer_readiness_score" in result.columns:
        result = result.sort_values("answer_readiness_score", ascending=False)

    OUTPUT_DIR.mkdir(exist_ok=True)
    result.to_csv(CSV_OUTPUT, index=False)
    JSON_OUTPUT.write_text(
        json.dumps(result.to_dict(orient="records"), indent=2, default=str),
        encoding="utf-8",
    )

    print(f"\nSaved: {CSV_OUTPUT}")
    print(f"Saved: {JSON_OUTPUT}")
    print("\nTop results:")
    cols = [c for c in ["label", "answer_readiness_score", "url"] if c in result.columns]
    print(result[cols].to_string(index=False))


if __name__ == "__main__":
    main()
