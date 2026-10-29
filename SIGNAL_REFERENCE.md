h1_count
Number of H1 headings found on the page.

h2_count
Number of H2 headings found on the page.

h3_count
Number of H3 headings found on the page.

question_heading_count
Number of H1-H3 headings that appear to be questions.

A heading counts when:
- it ends in "?"
- or begins with a question word such as:
  who, what, when, where, why, how, can, does, do, is, are, should, which

Purpose:
Measures how directly the page organizes information around user questions.

---

REFERENCES

Number of headings followed by a paragraph containing approximately
15-80 words.

Purpose:
Looks for short, directly extractable answer passages immediately
following headings.

Important:
This currently uses relatively strict HTML structure detection.
Accordion or deeply nested FAQ content may be undercounted.

---

SCANNABILITY 

list_count
Number of unordered and ordered lists:
- <ul>
- <ol>

Purpose:
Lists can make information easier to scan and extract.

table_count
Number of HTML tables on the page.

Purpose:
Measures structured presentation of facts or comparisons.

---

DATA STRUCTURE

jsonld_present
Whether the page contains JSON-LD structured data.

schema_types
The @type values found inside JSON-LD markup.

Examples:
- Article
- NewsArticle
- FAQPage
- HowTo
- Organization
- WebPage

faq_schema
Whether FAQPage schema was detected.

howto_schema
Whether HowTo schema was detected.

article_schema
Whether Article, NewsArticle, or BlogPosting schema was detected.

---

METADATA

meta_description_present
Whether the page contains a meta description.

canonical_present
Whether a canonical URL tag is present.

date_hint_present
Whether a publication or modification date could be detected.

date_hint
The date value found, when available.

---
SOURCES & AUTHORITY

outbound_link_count
Number of links pointing to another domain.

reference_section_count
Number of headings containing terms such as:
- References
- Sources
- Resources
- Citations
- Further Reading
- Related Resources

Purpose:
Looks for visible sourcing or supporting-resource structure.

---

CHARACTERISTICS

word_count
Approximate total number of words extracted from the page.

avg_paragraph_words
Average number of words per paragraph.

internal_link_count
Number of links pointing elsewhere on the same domain.

---

AEO-GEO Readiness Monitor Score

The final score is a deterministic heuristic from 0-100.

Current categories:

- Semantic hierarchy: up to 15 points
- Answer formatting: up to 20 points
- Scannability: up to 15 points
- Structured data: up to 15 points
- Metadata: up to 12 points
- Source signals: up to 13 points
- Readability: up to 10 points

The score is intended for structural comparison only.

It does not predict rankings, citations, or visibility in ChatGPT,
Google AI Overviews, Gemini, Perplexity, or other answer engines.