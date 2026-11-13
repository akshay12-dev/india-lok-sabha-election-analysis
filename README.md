# 🇮🇳 Election Analysis Application (2009–2024)

An interactive, stand-alone desktop analytics application investigating how popular vote shares translate into parliamentary seats under India's First-Past-The-Post (FPTP) system across four general elections (2009, 2014, 2019, 2024).

---

## 🚀 Running the Application

Double-click **`Launch_App.bat`** in the project folder, or run:
```bash
python desktop_app.py
```

*Launches a native desktop window powered by embedded Chromium (PySide6 QtWebEngine) with desktop window controls, keyboard shortcuts (F5 to reload, F11 for fullscreen, Ctrl+Q to exit), automated local port allocation, and clean background process management.*

---

## ⚡ Key Capabilities
- **Direct PC File Ingestion**: Upload any raw election CSV file directly from your computer (drag & drop or browse).
- **Automated Data Cleaning Engine**: Normalizes political parties, calculates candidate vote rankings per constituency, computes margins of victory, handles uncontested seats, and calculates the Gallagher Disproportionality Index.
- **5 Sample Raw Datasets Included**: Ready-to-use sample raw files for instant testing.
- **Interactive Multi-Tab Dashboard**: National overview, coalition/alliance breakdown, state heatmaps, and constituency deep-dives.

---

## 📁 Original Election Raw CSV Files (in `original_election_files/`)

Official constituency-wise detailed results from India Data Portal / ECI, ready for you to upload from your PC:

| File | Rows | Size | Description |
|---|---|---|---|
| `original_election_2024.csv` | 8,901 | 1.77 MB | Official 2024 General Election raw constituency detailed results |
| `original_election_2019.csv` | 8,597 | 1.70 MB | Official 2019 General Election raw constituency detailed results |
| `original_election_2014.csv` | 8,355 | 1.50 MB | Official 2014 General Election raw constituency detailed results |
| `original_election_2009.csv` | 8,070 | 1.40 MB | Official 2009 General Election raw constituency detailed results |
| `original_election_complete_2009_2024.csv` | 33,923 | 6.37 MB | Complete combined 2009–2024 official raw election results |

---

## 🧪 Dummy Sample Raw Datasets (in `data/raw/`)

| File | Rows | Description |
|---|---|---|
| `dummy_sample_national_2024.csv` | 683 | Synthetic raw dataset with 100 dummy constituencies across 10 states |
| `dummy_sample_multi_year_2019_2024.csv` | 634 | Multi-year synthetic dataset across 2019 & 2024 for longitudinal trend testing |
| `dummy_sample_competitive_races.csv` | 336 | High-competition synthetic dataset where all 50 seats have <5% victory margins |
| `dummy_sample_quick_test.csv` | 153 | Compact synthetic raw dataset (20 constituencies) for quick upload testing |

*Select any dummy sample in the application sidebar, or download it to your PC to test the raw file uploader.*

---

## 📱 Application Modules & Visualizations

1. **🛠️ Automated Ingestion & Cleaning Report**:
   - Displays real-time metrics on raw rows ingested, cleaned candidate records, unique constituencies validated, duplicates removed, and uncontested seats handled.

2. **📊 National Overview & Proportionality**:
   - **KPI Cards**: Gallagher Disproportionality Index, Competitive Seats (< threshold lead), Seats Declared, Median Winning Margin.
   - **Comparative Visuals**: Side-by-side popular vote share vs seat share bar charts for selected parties.
   - **Seat/Vote Multiplier**: Historical trend lines showing parliamentary bonus or penalty (1.0 = proportional parity).
   - **Winning Margin Distribution**: Histogram of victory leads with customizable margin threshold slider.
   - **Disproportionality History**: Longitudinal Gallagher Index progression across elections.

3. **🤝 Coalitions & Alliances**:
   - Compares major coalitions: **NDA** vs **INDIA / UPA** vs **Others**.
   - Analysis of how coalition pacts consolidate votes under First-Past-The-Post.
   - Aggregate seat counts, coalition vote shares, and seat shares.

4. **🗺️ State-by-State Footprint**:
   - Interactive state-level vote share heatmap across general elections.
   - State-wise seats won bar charts for any chosen national or regional party.

5. **🔍 Constituency Explorer**:
   - Deep dive into any specific constituency in any state for any election year.
   - Instant winner name, winning party, victory margin (raw votes and percentage of total polled).
   - Candidate breakdown chart and table showing all contenders, ranks, votes, and vote shares.

6. **📑 Methodology & Clean Data Export**:
   - Explanations of First-Past-The-Post dynamics and the Gallagher Index formula.
   - One-click CSV download buttons for the currently processed party summary, margins, and candidate tables.

---

## 🛠️ Installation & Requirements

```bash
pip install -r requirements.txt
```
Dependencies:
- `pandas>=2.2`, `numpy>=1.26,<3`
- `plotly>=5.18`, `streamlit>=1.30`
- `PySide6>=6.5`
- `pytest>=7.0` (for testing)

---

## 🔍 Data Completeness & Testing

- **Run Data Completeness Audit**:
  ```bash
  python diagnose_missing_data.py
  ```
  *Audits all 543 constituencies per year and prints actionable instructions for recovering missing states (e.g., 2014 Chhattisgarh & Odisha).*

- **Run Unit Tests**:
  ```bash
  pytest tests/ -v
  ```
  *Executes hand-verifiable unit tests for Gallagher Index, party summaries, victory margins, and uncontested seats.*

---

## 📦 Converting to Standalone Windows EXE (PyInstaller)

To bundle this application into an independent `.exe`:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "ElectionAnalysisApp" --add-data "app;app" --add-data "src;src" --add-data "data/raw;data/raw" --add-data "original_election_files;original_election_files" --add-data "alliances.json;." desktop_app.py
```
*The resulting distribution will be located in the `dist/ElectionAnalysisApp/` folder, ready to run without requiring a Python installation.*
