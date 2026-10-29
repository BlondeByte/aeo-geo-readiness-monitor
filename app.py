from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path("output/aeo_audit.csv")

st.set_page_config(page_title="AEO Answer Readiness Auditor", layout="wide")

st.title("AEO / GEO Answer Readiness Auditor")
st.caption(
    "Deterministic structural analysis. The score is a comparison heuristic, "
    "not a prediction of AI ranking or citation."
)

if not DATA_FILE.exists():
    st.warning("No audit output found. Run `python3 analyzer.py` first.")
    st.stop()

df = pd.read_csv(DATA_FILE)

if "error" in df.columns:
    bad = df[df["error"].fillna("").astype(str).str.len() > 0]
    if not bad.empty:
        st.error(f"{len(bad)} page(s) returned an analysis error.")

clean = df.copy()
if "answer_readiness_score" in clean.columns:
    clean["answer_readiness_score"] = pd.to_numeric(
        clean["answer_readiness_score"], errors="coerce"
    ).fillna(0)

c1, c2, c3 = st.columns(3)
c1.metric("Pages analyzed", len(clean))
c2.metric(
    "Average score",
    f"{clean['answer_readiness_score'].mean():.1f}" if len(clean) else "0"
)
c3.metric(
    "Highest score",
    f"{clean['answer_readiness_score'].max():.0f}" if len(clean) else "0"
)

st.subheader("Ranked pages")
rank_cols = [
    c for c in [
        "label", "answer_readiness_score", "question_heading_count",
        "concise_answer_count", "list_count", "table_count",
        "jsonld_present", "reference_section_count", "url"
    ] if c in clean.columns
]
st.dataframe(
    clean[rank_cols].sort_values("answer_readiness_score", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Score comparison")
chart_df = clean[["label", "answer_readiness_score"]].dropna()
if not chart_df.empty:
    st.bar_chart(chart_df.set_index("label"))

st.subheader("Inspect a page")
labels = clean["label"].fillna(clean["url"]).astype(str).tolist()
selected = st.selectbox("Page", labels)

row = clean[clean["label"].astype(str) == selected]
if row.empty:
    row = clean.iloc[[0]]

record = row.iloc[0]
detail_cols = [
    "url", "rights_basis", "rights_page_url", "title",
    "answer_readiness_score", "h1_count", "h2_count", "h3_count",
    "question_heading_count", "concise_answer_count", "list_count",
    "table_count", "word_count", "avg_paragraph_words",
    "outbound_link_count", "reference_section_count",
    "jsonld_present", "schema_types", "canonical_present",
    "date_hint_present", "date_hint", "score_breakdown"
]
for col in detail_cols:
    if col in record.index:
        st.write(f"**{col}:** {record[col]}")
