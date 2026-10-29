# Recording checklist

## Before recording
- [ ] ChatGPT / other AI tools closed
- [ ] All code finished and locally available
- [ ] Every input page manually rights-checked
- [ ] `rights_basis` completed
- [ ] `rights_page_url` completed
- [ ] `human_approved=YES` only for approved pages
- [ ] Test `python3 analyzer.py`
- [ ] Test `streamlit run app.py`
- [ ] Remove any personal information from screen / browser / terminal
- [ ] Clear notifications
- [ ] Have 5-8 approved URLs ready
- [ ] Confirm the entire demo can be done in one continuous take

## Narration beats
1. Problem: AEO/GEO analysis needs observable, comparable structure signals.
2. Rights gate: only explicitly approved pages are analyzed.
3. Inputs: show URL sheet.
4. Method: explain deterministic HTML extraction, no LLM during run.
5. Run analyzer.
6. Inspect CSV.
7. Open dashboard.
8. Compare highest and lowest pages.
9. Manually validate one result against the original page.
10. Limitations: score is a heuristic, not a ranking/citation prediction.
11. Next experiment: compare structural scores with separately observed AI citations.
