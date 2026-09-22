# U.S. Births 2025 — CDC Provisional Natality Dashboard

Interactive Streamlit dashboard for exploring **birth counts** (not rates) across the 50 states + DC,
by month and infant sex, using CDC WONDER provisional 2025 natality data.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
| File | Purpose |
|---|---|
| `app.py` | The whole dashboard: data loading, validation, filters, KPIs, charts, tabs |
| `data/Provisional_Natality_2025_CDC.xlsx` | Original CDC workbook (never modified) |
| `requirements.txt` | Python packages Streamlit Cloud installs |
| `.streamlit/config.toml` | Light theme with a colorblind-safe accent color |

## Key design decisions (for students)
- **Counts, not rates.** The file has no population figures, so no birth rates or percentages are calculated.
- **Provisional data.** CDC may revise these numbers; the dashboard says so up front.
- **Month order.** Months are sorted by CDC *Month Code* (1–12), not alphabetically.
- **Zero-based axes.** Bar and line charts start at 0 so small differences are not exaggerated.
- **Validation.** On load, the app checks 1,224 rows, 51 geographies, 12 months, 2 sexes,
  0 missing, 0 duplicates, and 3,604,640 total births (see the *About the Data* tab).
- **Caching.** `st.cache_data` loads the workbook once instead of on every click.
- **Portable paths.** The data path is built from the location of `app.py`, so it works locally and on Streamlit Community Cloud.

Source: CDC WONDER, Provisional Natality — National Center for Health Statistics.
