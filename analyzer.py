import os
import sys
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("AEO_Auditor")

# ---------------------------------------------------------------------------
# Path & Environment Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
URLS_FILE = BASE_DIR / "urls.csv"
OUTPUT_CSV = BASE_DIR / "aeo_audit_results.csv"
OUTPUT_JSON = BASE_DIR / "aeo_audit_results.json"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 (AEO-GEO-Auditor/1.0)"
)
REQUEST_TIMEOUT_SECONDS = 12

HIGH_VALUE_SCHEMAS = {
    "article",
    "faqpage",
    "howto",
    "product",
    "organization",
    "techarticle",
    "newsarticle",
}


# ---------------------------------------------------------------------------
# Network & Extraction Helpers
# ---------------------------------------------------------------------------
def fetch_page_content(url: str, user_agent: str = DEFAULT_USER_AGENT) -> str | None:
    """Fetch raw HTML content from target URL with standard headers and error handling."""
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as err:
        logger.warning("Failed to fetch %s: %s", url, err)
        return None


def is_external_link(target_url: str, base_netloc: str) -> bool:
    """Determine whether a hyperlink resolves to an external domain."""
    parsed = urlparse(target_url)
    return bool(parsed.netloc and parsed.netloc.lower() != base_netloc.lower())


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------
def extract_page_features(html: str, target_url: str) -> dict:
    """Parse HTML and extract structural, schema, readability, and authority signals."""
    soup = BeautifulSoup(html, "html.parser")
    base_netloc = urlparse(target_url).netloc

    # 1. Information Architecture & Hierarchy
    h1_tags = soup.find_all("h1")
    h2_tags = soup.find_all("h2")
    h3_tags = soup.find_all("h3")
    semantic_containers = soup.find_all(["article", "section", "main", "aside"])

    # 2. Structured Data & Schema Validation
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    parsed_schemas = []
    schema_types_found = []

    for script in json_ld_scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string.strip())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if "@graph" in item and isinstance(item["@graph"], list):
                        for sub_item in item["@graph"]:
                            if isinstance(sub_item, dict) and "@type" in sub_item:
                                st = sub_item["@type"]
                                (
                                    schema_types_found.extend(st)
                                    if isinstance(st, list)
                                    else schema_types_found.append(st)
                                )
                    elif "@type" in item:
                        st = item["@type"]
                        (
                            schema_types_found.extend(st)
                            if isinstance(st, list)
                            else schema_types_found.append(st)
                        )
            parsed_schemas.append(data)
        except (json.JSONDecodeError, TypeError):
            continue

    normalized_schema_types = {str(t).lower() for t in schema_types_found}

    # 3. Direct-Answer Syntactic Scannability
    lists = soup.find_all(["ul", "ol"])
    max_list_items = 0
    for lst in lists:
        items = lst.find_all("li", recursive=False)
        max_list_items = max(max_list_items, len(items))

    tables = soup.find_all("table")
    has_valid_table = any(t.find("tr") and (t.find("th") or t.find("td")) for t in tables)

    # Paragraph density (search for 40-80 word target definition paragraphs)
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
    word_counts = [len(p.split()) for p in paragraphs if p]
    has_target_definition_para = any(40 <= wc <= 80 for wc in word_counts)

    # 4. Citation & Authority Metadata
    meta_desc_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""

    author_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "author"})
    has_author = bool(
        (author_tag and author_tag.get("content", "").strip())
        or soup.find(attrs={"rel": "author"})
        or soup.select(".author, .byline, [itemprop='author']")
    )

    canonical_tag = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    has_canonical = bool(canonical_tag and canonical_tag.get("href", "").strip())

    links = soup.find_all("a", href=True)
    external_links = [
        link["href"] for link in links if is_external_link(link["href"], base_netloc)
    ]

    return {
        "url": target_url,
        "h1_count": len(h1_tags),
        "h2_count": len(h2_tags),
        "h3_count": len(h3_tags),
        "has_semantic_containers": len(semantic_containers) > 0,
        "has_json_ld": len(parsed_schemas) > 0,
        "schema_types": list(normalized_schema_types),
        "max_list_items": max_list_items,
        "has_table": has_valid_table,
        "has_target_definition_para": has_target_definition_para,
        "meta_desc_len": len(meta_desc),
        "has_author": has_author,
        "has_canonical": has_canonical,
        "external_link_count": len(external_links),
    }


# ---------------------------------------------------------------------------
# Scoring Rubric Implementation (100-Point Model)
# ---------------------------------------------------------------------------
def calculate_aeo_score(features: dict) -> dict:
    """Compute dimensional and composite AEO/GEO readiness scores according to SCORING_REFERENCES.md."""
    # 1. Information Architecture & Hierarchy (Max 25 pts)
    h1_score = 10 if features.get("h1_count", 0) == 1 else 0

    h2_count = features.get("h2_count", 0)
    if h2_count >= 2:
        h2_score = 10
    elif h2_count == 1:
        h2_score = 5
    else:
        h2_score = 0

    semantic_score = 5 if features.get("has_semantic_containers", False) else 0
    subtotal_hierarchy = h1_score + h2_score + semantic_score

    # 2. Structured Data & Schema Markup (Max 25 pts)
    json_ld_presence = 15 if features.get("has_json_ld", False) else 0

    schemas_present = set(features.get("schema_types", []))
    if schemas_present & HIGH_VALUE_SCHEMAS:
        schema_type_score = 10
    elif len(schemas_present) > 0:
        schema_type_score = 5
    else:
        schema_type_score = 0

    subtotal_schema = json_ld_presence + schema_type_score

    # 3. Direct-Answer Syntactic Scannability (Max 30 pts)
    max_list = features.get("max_list_items", 0)
    if max_list >= 3:
        list_score = 10
    elif max_list > 0:
        list_score = 5
    else:
        list_score = 0

    table_score = 10 if features.get("has_table", False) else 0
    definition_score = 10 if features.get("has_target_definition_para", False) else 0
    subtotal_scannability = list_score + table_score + definition_score

    # 4. Citation & Authority Metadata (Max 20 pts)
    desc_len = features.get("meta_desc_len", 0)
    if 70 <= desc_len <= 160:
        desc_score = 5
    elif desc_len > 0:
        desc_score = 2
    else:
        desc_score = 0

    author_score = 5 if features.get("has_author", False) else 0
    canonical_score = 5 if features.get("has_canonical", False) else 0
    external_link_score = 5 if features.get("external_link_count", 0) >= 2 else 0
    subtotal_authority = (
        desc_score + author_score + canonical_score + external_link_score
    )

    # Composite Score & Tier Assignment
    total_score = (
        subtotal_hierarchy
        + subtotal_schema
        + subtotal_scannability
        + subtotal_authority
    )

    if total_score >= 90:
        readiness_tier = "Tier 1: High Extraction Probability"
    elif total_score >= 75:
        readiness_tier = "Tier 2: Moderate GEO Suitability"
    elif total_score >= 55:
        readiness_tier = "Tier 3: Sub-optimal Readiness"
    else:
        readiness_tier = "Tier 4: Low Extraction Readiness"

    return {
        "url": features.get("url", ""),
        "total_score": total_score,
        "readiness_tier": readiness_tier,
        "score_hierarchy": subtotal_hierarchy,
        "score_schema": subtotal_schema,
        "score_scannability": subtotal_scannability,
        "score_authority": subtotal_authority,
        "h1_count": features.get("h1_count", 0),
        "h2_count": features.get("h2_count", 0),
        "has_schema": features.get("has_json_ld", False),
        "matched_schemas": ", ".join(features.get("schema_types", [])) if features.get("schema_types") else "None",
        "has_tables": features.get("has_table", False),
        "has_lists": features.get("max_list_items", 0) > 0,
        "external_links": features.get("external_link_count", 0),
    }


# ---------------------------------------------------------------------------
# Main Orchestration Loop
# ---------------------------------------------------------------------------
def run_auditor() -> None:
    """Read URLs, execute audits across targets, and export structured results."""
    if not URLS_FILE.exists():
        logger.error("Missing input file: %s. Please create it with target URLs.", URLS_FILE)
        sys.exit(1)

    try:
        urls_df = pd.read_csv(URLS_FILE)
        if "url" in urls_df.columns:
            url_col = "url"
        else:
            url_col = urls_df.columns[0]
            logger.info("Using first column '%s' as URL source.", url_col)

        target_urls = [
            str(u).strip()
            for u in urls_df[url_col].dropna()
            if str(u).strip().startswith("http")
        ]
    except Exception as err:
        logger.error("Failed to read %s: %s", URLS_FILE, err)
        sys.exit(1)

    if not target_urls:
        logger.warning("No valid HTTP/HTTPS URLs found in %s.", URLS_FILE)
        return

    logger.info("Found %d target URLs. Commencing audit...", len(target_urls))
    audit_records = []

    for idx, url in enumerate(target_urls, start=1):
        logger.info("[%d/%d] Fetching: %s", idx, len(target_urls), url)
        html = fetch_page_content(url)
        if not html:
            logger.warning("Skipping %s due to fetch failure.", url)
            continue

        try:
            features = extract_page_features(html, url)
            score_data = calculate_aeo_score(features)
            audit_records.append(score_data)
            logger.info(
                "Audited %s -> Score: %d/100 (%s)",
                url,
                score_data["total_score"],
                score_data["readiness_tier"],
            )
        except Exception as err:
            logger.error("Error analyzing %s: %s", url, err)

    if not audit_records:
        logger.warning("No audit records generated. Exports skipped.")
        return

    # Export to DataFrame and CSV
    results_df = pd.DataFrame(audit_records)
    results_df.sort_values(by="total_score", ascending=False, inplace=True)
    results_df.to_csv(OUTPUT_CSV, index=False)
    logger.info("Exported CSV results -> %s", OUTPUT_CSV.name)

    # Export to JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_records, f, indent=2)
    logger.info("Exported JSON results -> %s", OUTPUT_JSON.name)
    logger.info("Audit run complete. Processed %d pages successfully.", len(audit_records))


if __name__ == "__main__":
    run_auditor()