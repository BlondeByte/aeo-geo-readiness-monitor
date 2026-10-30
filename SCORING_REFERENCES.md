CONTENT STRUCTURE: Measure how directly the page organizes information around user questions

#SEMANTIC HIERARCHY
h1_count
Number of H1 headings found on the page

h2_count
Number of H2 headings found on the page

h3_count
Number of H3 headings found on the page

question_heading_count
Number of H1-H3 headings that appear to be questions

A heading counts when:
it ends in "?"
or begins with a question word such as:
who, what, when, where, why, how, can, does, do, is, are, should, which

#ANSWER FORMATTING: Looks for short, directly extractable answer passages immediately following headings

concise_answer_count
Number of headings followed by a paragraph containing approximately 15-80 words.
This currently uses relatively strict HTML structure detection.
Accordion or deeply nested FAQ content may be undercounted.

#SCANNABILITY: Measure presentation of facts or comparisons

list_count: can make information easier to scan/extract
Number of unordered and ordered lists:
- <ul>
- <ol>

table_count: number of HTML tables on page

#STRUCTURED DATA

jsonld_present
Whether the page contains JSON-LD structured data.

schema_types
The @type values found inside JSON-LD markup.

Examples in Analyzer:
Article, NewsArticle, FAQPage, HowTo, Organization, WebPage

faq_schema
Is FAQPage schema detected

howto_schema
Is HowTo schema detected

article_schema
Any Article, NewsArticle, or BlogPosting schema detected

#METADATA

meta_description_present
Whether the page contains a meta description.

date_hint_present
Whether a publication or modification date could be detected.

date_hint
The date value found, when available.

#SOURCE SIGNALS
Search for visible sourcing or supporting-resource structures

outbound_link_count
Number of links pointing to another domain.

reference_section_count
Number of headings containing terms such as:
References
Sources
Resources
Citations
Further Reading
Related Resources

#READABILITY
word_count
avg_paragraph_words
internal_link_count

DELIVERABLE! 
ANSWER READINESS SCORE: Deterministic from 1-100

Categories:
Semantic hierarchy: up to 15 points
Answer formatting: up to 20 points
Scannability: up to 15 points
Structured data: up to 15 points
Metadata: up to 12 points
Source signals: up to 13 points
Readability: up to 10 points