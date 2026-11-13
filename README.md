# Lok Sabha Election Analysis (2009–2024)

An interactive desktop analytics application that shows how popular vote share turns into
parliamentary seats under India's First-Past-The-Post (FPTP) system, across four general
elections: **2009, 2014, 2019 and 2024**.

Built with Streamlit for the interface, wrapped in a native PySide6 window so it runs as a
stand-alone desktop app.

---

## Quick Start

Double-click **`Launch_App.bat`**, or run one of:

```bash
python desktop_app.py          # native desktop window (recommended)
streamlit run app/app.py       # browser mode
```

The desktop wrapper embeds Chromium (QtWebEngine), picks a free local port, and supports
`F5` reload, `F11` fullscreen and `Ctrl+Q` to quit.

First-time setup:

```bash
pip install -r requirements.txt
```

---

## What the App Does

### Data ingestion
- **Upload any raw election CSV from your PC** (drag & drop or browse) — no fixed schema needed.
- **Four built-in synthetic sample datasets** for instant demo/testing without uploading anything.
- **Automated cleaning engine**: normalises party names, ranks candidates per constituency,
  computes victory margins, detects uncontested seats, handles the 2024 Surat by-poll,
  and calculates the Gallagher Disproportionality Index.

### Five analysis tabs

1. **National Overview & Proportionality**
   KPI cards with change vs. the previous election, popular vote vs. seat share bars,
   vote-to-seat multiplier trends, winning-margin histogram with an adjustable
   competitiveness threshold, the Gallagher gauge, and longitudinal disproportionality history.

2. **Coalitions & Alliances**
   Parliament hemicycle of the 543 seats, NDA vs. INDIA/UPA vs. Others comparison, and a
   Sankey diagram tracing parties into alliance blocs. Alliance membership is configured in
   `alliances.json` for each election year.

3. **State-by-State Footprint**
   Ranked state-level vote-share heatmap with gainers/losers, plus state-wise seats won for
   any selected party.

4. **Constituency Explorer**
   Quick picks (closest races, biggest landslides), winner spotlight card, candidate donut
   chart, and a full candidate table with ranks, votes and vote shares.

5. **Methodology & Clean Data Export**
   Plain-English explanation of FPTP and the Gallagher Index formula, plus one-click CSV
   downloads of the processed party summary, margins and candidate-level tables.

### Extras
- **Compare Elections mode** — any two years side by side.
- **Timeline slider with auto-play** for longitudinal animation.
- **Plain-English insights panel** generated from the active data.
- **Dark / light theme** toggle with Indian tricolour accents.
- "How to read this chart" expanders for every major visualisation.

---

## Project Structure

```
.
├── app/
│   ├── app.py               # Streamlit UI (layout, tabs, sidebar, interactions)
│   ├── theme.py             # Colours, Plotly templates, chart builders
│   └── assets/style.css     # Custom CSS (cards, tabs, sidebar)
├── src/
│   └── elections.py         # Cleaning + analysis engine (no Streamlit dependency)
├── data/
│   ├── raw/                 # 4 synthetic sample datasets
│   └── clean/               # Destination for exported/clean CSVs
├── original_election_files/ # Official raw ECI / India Data Portal CSVs
├── tests/test_elections.py  # Pytest suite for the analysis engine
├── alliances.json           # Alliance membership per election year
├── desktop_app.py           # Native PySide6 desktop wrapper
├── Launch_App.bat           # One-click Windows launcher
├── diagnose_missing_data.py # Data completeness audit (543-seat check)
└── requirements.txt
```

---

## Data

### Official raw files (`original_election_files/`)

Candidate-level constituency results from the Election Commission of India / India Data Portal,
ready to upload from the app sidebar:

| File | Rows | Size |
|---|---|---|
| `original_election_2009.csv` | 8,070 | 1.40 MB |
| `original_election_2014.csv` | 8,355 | 1.50 MB |
| `original_election_2019.csv` | 8,597 | 1.70 MB |
| `original_election_2024.csv` | 8,901 | 1.77 MB |
| `original_election_complete_2009_2024.csv` | 33,923 | 6.37 MB |

### Built-in sample datasets (`data/raw/`)

| File | Rows | Description |
|---|---|---|
| `dummy_sample_national_2024.csv` | 683 | 100 synthetic constituencies across 10 states |
| `dummy_sample_multi_year_2019_2024.csv` | 634 | Synthetic 2019 + 2024 data for trend testing |
| `dummy_sample_competitive_races.csv` | 336 | 50 seats, all with < 5% victory margins |
| `dummy_sample_quick_test.csv` | 153 | Compact 20-constituency dataset |

### Known data gaps

The official source files are not 100% complete, and the app flags this in the UI:

| Year | Seats present | Missing |
|---|---|---|
| 2014 | 511 / 543 | Chhattisgarh (11), Odisha (21) |
| 2009 | 541 / 543 | Andaman & Nicobar Islands (1), Nainital-Udhamsingh Nagar (1) |
| 2019 | 543 / 543 | — |
| 2024 | 543 / 543 | — |

Run the audit for a detailed, state-by-state report with recovery instructions:

```bash
python diagnose_missing_data.py
```

**No data is fabricated, extrapolated or estimated.** Every row must come from an official
ECI source; gaps are reported rather than filled.

---

## Development

### Tests

```bash
pytest tests/ -v
```

Covers the Gallagher Index, party summaries, victory margins and uncontested-seat handling
against hand-verifiable numbers.

### Dependencies

`requirements.txt`:

- `pandas>=2.2`, `numpy>=1.26,<3`
- `plotly>=5.18`, `streamlit>=1.30`
- `PySide6>=6.5`
- `pytest>=7.0`

### Building a stand-alone Windows executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "ElectionAnalysisApp" ^
  --add-data "app;app" --add-data "src;src" --add-data "data/raw;data/raw" ^
  --add-data "original_election_files;original_election_files" ^
  --add-data "alliances.json;." desktop_app.py
```

The distributable lands in `dist/ElectionAnalysisApp/` and runs without a Python install.

---

## Notes

- Errors from the desktop wrapper are written to `desktop_server.log` (regenerated on each launch).
- Data sources: Election Commission of India, India Data Portal.
