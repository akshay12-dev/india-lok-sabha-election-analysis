"""Election Analysis Application (2009–2024).

Features:
- Responsive, polished UI with Indian Tricolour accents (saffron, green, navy)
- Dark Mode (Default) & Light Mode toggle
- Glassmorphism KPI cards with previous election deltas (Δ)
- Timeline slider with auto-play animation mode
- Compare Elections mode (side-by-side comparison with Δ metrics)
- Parliament Hemicycle & Party-to-Alliance Sankey diagrams
- Vote vs Seat Share Proportionality Scatter Bubble plot
- Ranked State Heatmap with grey NaNs and Gainers/Losers panel
- Constituency Explorer with Quick-Picks (closest races & landslides), Winner Spotlight Card, and Donut Chart
- Auto-generated plain-English AI Insights panel
- Pedagogical "How to read this chart" expanders

Data Sources: India Data Portal / ECI.

Run via:
    python desktop_app.py
    streamlit run app/app.py
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# PyInstaller / frozen executable resource resolution
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = ROOT / "src"
APP_DIR = ROOT / "app"
for d in [SRC_DIR, APP_DIR]:
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

import elections as e  # noqa: E402
import theme as th  # noqa: E402

st.set_page_config(
    page_title="Lok Sabha Election Analysis (2009–2024)",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

RAW_DIR = ROOT / "data/raw"

OFFICIAL_RAW = RAW_DIR / "lok_sabha_combined.csv"
if not OFFICIAL_RAW.exists():
    OFFICIAL_RAW = ROOT / "original_election_files" / "original_election_complete_2009_2024.csv"

SAMPLE_OPTIONS = {
    "Official Lok Sabha Raw Dataset (2009–2024)": OFFICIAL_RAW,
    "Dummy Sample 1: National Election 2024 (100 seats, 683 mock candidates)": RAW_DIR / "dummy_sample_national_2024.csv",
    "Dummy Sample 2: Multi-Year Longitudinal (2019 & 2024, 634 mock candidates)": RAW_DIR / "dummy_sample_multi_year_2019_2024.csv",
    "Dummy Sample 3: Competitive Close Races (<5% margin, 50 seats)": RAW_DIR / "dummy_sample_competitive_races.csv",
    "Dummy Sample 4: Quick-Demo Compact (20 seats, 153 mock candidates)": RAW_DIR / "dummy_sample_quick_test.csv",
}


# ── CSS Injection ─────────────────────────────────────────────────────────────
def load_css(theme_mode: str = "dark"):
    """Loads external stylesheet and injects theme mode CSS variables."""
    css_path = APP_DIR / "assets" / "style.css"
    base_css = ""
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            base_css = f.read()

    is_dark = theme_mode.lower() == "dark"

    if is_dark:
        theme_vars = """
        :root {
            --bg-page: #0E1117;
            --bg-surface: #161B22;
            --bg-card: #161B22;
            --bg-card-hover: #1F242C;
            --tab-bg: #161B22;
            --border-subtle: rgba(255, 255, 255, 0.12);
            --border-accent: rgba(255, 153, 51, 0.4);
            --text-primary: #F0F6FC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --card-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
        }
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
            background-color: #0E1117 !important;
            color: #F0F6FC !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child, [data-testid="stSidebarContent"] {
            background-color: #161B22 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stMarkdown {
            color: #F0F6FC !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #F0F6FC !important;
        }
        .stApp small, .stCaption, [data-testid="stCaptionContainer"] {
            color: #94A3B8 !important;
        }
        .kpi-card, .hero-header, .timeline-card, .winner-card, .insights-panel {
            background-color: #161B22 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #F0F6FC !important;
        }
        .hero-title, .kpi-value, .winner-card-title {
            color: #F0F6FC !important;
        }
        .hero-subtitle, .kpi-label {
            color: #94A3B8 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #161B22 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94A3B8 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #FFFFFF !important;
        }
        [data-baseweb="select"] > div, [data-baseweb="base-input"], input, textarea {
            background-color: #1F242C !important;
            color: #F0F6FC !important;
            border-color: rgba(255, 255, 255, 0.15) !important;
        }
        [data-testid="stExpander"] {
            background-color: #161B22 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
        }
        """
    else:
        theme_vars = """
        :root {
            --bg-page: #F8FAFC;
            --bg-surface: #FFFFFF;
            --bg-card: #FFFFFF;
            --bg-card-hover: #F1F5F9;
            --tab-bg: #EDF2F7;
            --border-subtle: rgba(0, 0, 0, 0.1);
            --border-accent: rgba(255, 153, 51, 0.45);
            --text-primary: #0F172A;
            --text-secondary: #475569;
            --text-muted: #94A3B8;
            --card-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        }
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child, [data-testid="stSidebarContent"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid rgba(0, 0, 0, 0.1) !important;
        }
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stMarkdown {
            color: #0F172A !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #0F172A !important;
        }
        .stApp small, .stCaption, [data-testid="stCaptionContainer"] {
            color: #64748B !important;
        }
        .kpi-card, .hero-header, .timeline-card, .winner-card, .insights-panel {
            background-color: #FFFFFF !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            color: #0F172A !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06) !important;
        }
        .hero-title, .kpi-value, .winner-card-title {
            color: #0F172A !important;
        }
        .hero-subtitle, .kpi-label {
            color: #64748B !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #EDF2F7 !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #4A5568 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #FFFFFF !important;
        }
        [data-baseweb="select"] > div, [data-baseweb="base-input"], input, textarea {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-color: rgba(0, 0, 0, 0.15) !important;
        }
        [data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            border-radius: 12px !important;
        }
        """

    # Global Deploy / Snowflake toolbar suppression while preserving sidebar toggle
    cloud_suppress = """
    [data-testid="stAppDeployButton"],
    .stDeployButton,
    [data-testid="stToolbarActions"],
    [data-testid="stStatusWidget"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    /* Explicitly keep sidebar unhide / expand button visible and clickable */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
        cursor: pointer !important;
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sm) !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        color: var(--text-primary) !important;
    }
    """

    st.markdown(f"<style>\n{base_css}\n{theme_vars}\n{cloud_suppress}\n</style>", unsafe_allow_html=True)


@st.cache_data
def process_cached_source(source_path_or_bytes):
    """Processes raw data through the cleaning pipeline and caches results."""
    return e.process_election_data(source_path_or_bytes)


# ── Sidebar & Ingestion ───────────────────────────────────────────────────────
def render_sidebar(theme_mode: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, dict | None, str]:
    """Renders the sidebar controls for theme, data ingestion, and settings."""
    st.sidebar.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:1.6rem;">🗳️</span>
            <div>
                <h3 style="margin:0; font-size:1.15rem; font-weight:800; letter-spacing:-0.02em;">Lok Sabha Analytics</h3>
                <span style="font-size:0.75rem; color:#888;">India Data Portal / ECI</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Theme Toggle
    current_mode = st.session_state.get("theme_mode", "dark")
    selected_theme = st.sidebar.radio(
        "🎨 Appearance Mode",
        ["Dark Mode", "Light Mode"],
        index=0 if current_mode == "dark" else 1,
        horizontal=True,
        key="app_theme_mode_selector",
    )
    new_theme = "dark" if selected_theme == "Dark Mode" else "light"
    if new_theme != current_mode:
        st.session_state["theme_mode"] = new_theme
        st.rerun()

    st.sidebar.markdown("---")

    # 2. Data Mode
    st.sidebar.subheader("📂 Ingestion Pipeline")
    data_mode = st.sidebar.radio(
        "Choose Ingestion Source:",
        ["Upload Raw CSV from PC", "Use Sample Dummy Raw Dataset"],
        index=0,
    )

    cleaning_stats = None
    full_df = None
    summary = None
    margins = None
    gi = None

    if data_mode == "Upload Raw CSV from PC":
        st.sidebar.markdown("**Upload Raw CSV file from your PC:**")
        uploaded_file = st.sidebar.file_uploader(
            "Choose raw CSV file",
            type=["csv"],
            help="Upload an official India Data Portal / ECI constituency-wise detailed results CSV.",
        )
        if uploaded_file is not None:
            try:
                with st.spinner("⚡ Cleaning candidate records..."):
                    bytes_data = uploaded_file.getvalue()
                    full_df, summary, margins, gi, cleaning_stats = e.process_election_data(io.BytesIO(bytes_data))
                st.sidebar.success(f"✓ Cleaned: {uploaded_file.name}")
            except Exception as ex:
                st.sidebar.error(f"Error parsing raw file: {ex}")
                st.stop()
        else:
            st.info("👆 Please select or drag & drop a raw election CSV file from your computer using the sidebar.")
            st.markdown(
                """
                ### 📂 Ready to Ingest & Clean Your Raw Data
                Upload any raw election CSV file from your computer using the file uploader in the sidebar.

                **The built-in processing pipeline will automatically:**
                - **Standardize schema**: Detects constituency, candidate, state, party, and vote columns.
                - **Normalize political parties**: Cleans aliases, acronyms, and variations across 50+ parties.
                - **Rank candidates**: Calculates candidate rankings and total valid votes per constituency.
                - **Compute victory margins**: Calculates winner leads and flags competitive seats (< 5% margin).
                - **Measure proportionality**: Generates the Gallagher Index and seat-to-vote ratios.
                - **Produce interactive dashboards**: Instantly populates all 5 analytical modules.
                """
            )
            st.stop()

    else:  # Use Sample Dummy Raw Dataset
        available_samples = {k: v for k, v in SAMPLE_OPTIONS.items() if v.exists()}
        if available_samples:
            selected_sample = st.sidebar.selectbox("Select Sample Dataset:", list(available_samples.keys()), index=0)
            sample_file_path = available_samples[selected_sample]
            with st.spinner("⚡ Running cleaning pipeline on raw dataset..."):
                full_df, summary, margins, gi, cleaning_stats = process_cached_source(str(sample_file_path))
            st.sidebar.success(f"✓ Auto-cleaned: {selected_sample.split(':')[0]}")
        else:
            st.sidebar.error("Sample datasets not found on disk. Please upload a raw CSV.")
            st.stop()

    st.sidebar.markdown("---")
    return full_df, summary, margins, gi, cleaning_stats, new_theme


# ── Hero Banner ───────────────────────────────────────────────────────────────
def render_hero_header(year: int, is_compare: bool, compare_years: list[int] | None = None):
    """Renders the top hero header banner with tricolour accents."""
    if is_compare and compare_years and len(compare_years) == 2:
        badge_html = f"""
        <div class="year-badge">
            <span>⚖️ Comparative Mode:</span>
            <b>{compare_years[0]}</b> vs <b>{compare_years[1]}</b>
        </div>
        """
        title_text = f"General Election Comparison — {compare_years[0]} vs {compare_years[1]}"
    else:
        badge_html = f"""
        <div class="year-badge">
            <span>📅 Election Year:</span>
            <b>{year}</b>
        </div>
        """
        title_text = f"Lok Sabha Election Analysis — General Election {year}"

    st.markdown(
        f"""
        <div class="hero-header">
            <div class="hero-title-row">
                <div>
                    <h1 class="hero-title">
                        <span>🇮🇳</span> {title_text}
                    </h1>
                    <p class="hero-subtitle">
                        An interactive investigation into popular vote shares, parliamentary seat bonuses,
                        coalition pacts, and victory margins under First-Past-The-Post.
                    </p>
                </div>
                {badge_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Glassmorphism KPI Metrics ─────────────────────────────────────────────────
def render_kpis(margins: pd.DataFrame, summary: pd.DataFrame, gi: pd.Series, year: int, threshold: float):
    """Renders the 4 modern glassmorphism KPI cards with previous election deltas."""
    available_years = sorted(int(y) for y in summary["year"].unique())
    prev_year = None
    if year in available_years:
        idx = available_years.index(year)
        if idx > 0:
            prev_year = available_years[idx - 1]

    # Current year metrics
    yr_margins = margins[margins["year"] == year]
    close_count = int((yr_margins["margin_pct"] < threshold).sum())
    total_seats = int(yr_margins.shape[0])
    median_margin = float(yr_margins["margin_pct"].median()) if not yr_margins.empty else 0.0
    curr_gi = float(gi.get(year, 0.0))

    # Delta calculations
    gi_delta_html = ""
    comp_delta_html = ""
    med_delta_html = ""

    if prev_year is not None:
        prev_margins = margins[margins["year"] == prev_year]
        prev_gi = float(gi.get(prev_year, 0.0))
        prev_close = int((prev_margins["margin_pct"] < threshold).sum())
        prev_median = float(prev_margins["margin_pct"].median()) if not prev_margins.empty else 0.0

        diff_gi = curr_gi - prev_gi
        diff_close = close_count - prev_close
        diff_median = median_margin - prev_median

        # Gallagher: lower is better (more proportional)
        if diff_gi < 0:
            gi_delta_html = f'<span class="kpi-delta positive">▼ {abs(diff_gi):.1f} vs {prev_year} (More Proportional)</span>'
        elif diff_gi > 0:
            gi_delta_html = f'<span class="kpi-delta negative">▲ {diff_gi:.1f} vs {prev_year} (Higher Disproportionality)</span>'
        else:
            gi_delta_html = f'<span class="kpi-delta neutral">0.0 vs {prev_year}</span>'

        # Competitive seats delta
        if diff_close > 0:
            comp_delta_html = f'<span class="kpi-delta positive">▲ {diff_close} vs {prev_year}</span>'
        elif diff_close < 0:
            comp_delta_html = f'<span class="kpi-delta neutral">▼ {abs(diff_close)} vs {prev_year}</span>'
        else:
            comp_delta_html = f'<span class="kpi-delta neutral">No change vs {prev_year}</span>'

        # Median margin delta
        if diff_median < 0:
            med_delta_html = f'<span class="kpi-delta positive">▼ {abs(diff_median):.1f}% vs {prev_year}</span>'
        else:
            med_delta_html = f'<span class="kpi-delta neutral">▲ {diff_median:.1f}% vs {prev_year}</span>'
    else:
        gi_delta_html = '<span class="kpi-delta neutral">Baseline Post-Delimitation</span>'
        comp_delta_html = f'<span class="kpi-delta neutral">{(close_count / total_seats * 100):.1f}% of seats' if total_seats > 0 else ""
        med_delta_html = '<span class="kpi-delta neutral">Historical Benchmark</span>'

    st.markdown(
        f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-label">
                    <span>Gallagher Index</span>
                    <span title="Least-squares measure of disproportionality. 0 = parity; higher denotes disproportionate seat bonus.">ℹ️</span>
                </div>
                <div class="kpi-value">{curr_gi:.1f}</div>
                <div>{gi_delta_html}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">
                    <span>Competitive Seats (&lt;{threshold}%)</span>
                    <span title="Seats decided by a razor-thin lead of less than the selected threshold.">ℹ️</span>
                </div>
                <div class="kpi-value">{close_count}</div>
                <div>{comp_delta_html}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">
                    <span>Constituencies in Margins</span>
                    <span title="542 in 2024 because Surat was won unopposed without a runner-up.">ℹ️</span>
                </div>
                <div class="kpi-value">{total_seats}</div>
                <div><span class="kpi-delta neutral">{'542 Contested + 1 Unopposed' if year == 2024 else 'Recorded Parliamentary Seats'}</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">
                    <span>Median Winning Margin</span>
                    <span title="Half of winning candidates had a victory margin smaller than this percentage.">ℹ️</span>
                </div>
                <div class="kpi-value">{median_margin:.1f}%</div>
                <div>{med_delta_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── AI Plain-English Insights Panel ───────────────────────────────────────────
def render_insights_panel(summary: pd.DataFrame, margins: pd.DataFrame, gi: pd.Series, year: int):
    """Computes and renders 3-4 plain-English takeaways for the selected year."""
    yr_sum = summary[summary["year"] == year].sort_values("seats", ascending=False)
    if yr_sum.empty:
        return

    top1 = yr_sum.iloc[0]
    top2 = yr_sum.iloc[1] if len(yr_sum) > 1 else None
    curr_gi = gi.get(year, 0.0)

    yr_margins = margins[margins["year"] == year]
    close_pct = (yr_margins["margin_pct"] < 5.0).mean() * 100 if not yr_margins.empty else 0.0

    insights = [
        f"<b>Majority Multiplier</b>: <b>{top1['party']}</b> secured <b>{top1['seat_share']:.1f}%</b> of parliamentary seats "
        f"with <b>{top1['vote_share']:.1f}%</b> of the national popular vote — translating to a seat-to-vote bonus multiplier of <b>{top1['seat_vote_ratio']:.2f}x</b>.",
    ]
    if top2 is not None:
        insights.append(
            f"<b>Runner-Up Dynamics</b>: <b>{top2['party']}</b> garnered <b>{top2['vote_share']:.1f}%</b> of the popular vote "
            f"and achieved <b>{top2['seats']}</b> seats ({top2['seat_share']:.1f}% seat share), reflecting a ratio of <b>{top2['seat_vote_ratio']:.2f}x</b>."
        )

    if curr_gi > 14.0:
        interp = "High disproportionality; FPTP delivered a decisive parliamentary seat bonus to the leading party."
    elif curr_gi > 7.5:
        interp = "Moderate disproportionality; competitive coalition dynamics mitigated national distortions."
    else:
        interp = "Low disproportionality; national seat shares closely matched broad voting strength."

    insights.append(f"<b>Electoral Proportionality</b>: Gallagher Index scored <b>{curr_gi:.1f}</b> ({interp}).")
    insights.append(f"<b>Close Contests</b>: <b>{close_pct:.1f}%</b> of all contested constituencies were decided by less than 5% margin.")

    items_html = "".join([f'<div class="insights-panel-item"><span>📌</span> <div>{item}</div></div>' for item in insights])

    st.markdown(
        f"""
        <div class="insights-panel">
            <div class="insights-panel-title">
                <span>💡 Key Takeaways & Analytical Insights ({year})</span>
            </div>
            {items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── TAB 1: National Overview & Proportionality ─────────────────────────────────
def render_tab_national(
    summary: pd.DataFrame,
    margins: pd.DataFrame,
    gi: pd.Series,
    year: int,
    chosen_parties: list[str],
    threshold: float,
    completeness_df: pd.DataFrame,
    theme_mode: str,
    is_compare: bool,
    compare_years: list[int],
):
    """Renders Tab 1: National Overview, Proportionality Scatter, Gauge, and Animation."""
    if not chosen_parties:
        st.warning("Please select at least one political party in the sidebar.")
        return

    # If Compare Mode is active:
    if is_compare and len(compare_years) == 2:
        y1, y2 = compare_years[0], compare_years[1]
        st.subheader(f"⚖️ Direct Election Comparison: {y1} vs {y2}")
        cmp_df = summary[summary["year"].isin([y1, y2]) & summary["party"].isin(chosen_parties)]

        p1 = cmp_df[cmp_df["year"] == y1].set_index("party")
        p2 = cmp_df[cmp_df["year"] == y2].set_index("party")

        diff_data = []
        for p in chosen_parties:
            s1 = p1.loc[p, "seats"] if p in p1.index else 0
            s2 = p2.loc[p, "seats"] if p in p2.index else 0
            v1 = p1.loc[p, "vote_share"] if p in p1.index else 0.0
            v2 = p2.loc[p, "vote_share"] if p in p2.index else 0.0
            diff_data.append({
                "Party": p,
                f"Seats ({y1})": int(s1),
                f"Seats ({y2})": int(s2),
                "Seat Δ": int(s2 - s1),
                f"Vote % ({y1})": round(v1, 2),
                f"Vote % ({y2})": round(v2, 2),
                "Vote % Δ": round(v2 - v1, 2),
            })
        st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_cmp_seats = px.bar(
                cmp_df,
                x="party",
                y="seats",
                color="year",
                barmode="group",
                text="seats",
                title=f"Seats Won Comparison ({y1} vs {y2})",
                labels={"party": "Party", "seats": "Seats Won", "year": "Year"},
                color_discrete_map={y1: "#00A3E0", y2: "#FF9933"},
            )
            st.plotly_chart(th.apply_chart_theme(fig_cmp_seats, theme_mode), use_container_width=True)

        with col_c2:
            fig_cmp_vote = px.bar(
                cmp_df,
                x="party",
                y="vote_share",
                color="year",
                barmode="group",
                text_auto=".1f",
                title=f"Popular Vote Share % Comparison ({y1} vs {y2})",
                labels={"party": "Party", "vote_share": "Vote Share (%)", "year": "Year"},
                color_discrete_map={y1: "#00A3E0", y2: "#FF9933"},
            )
            st.plotly_chart(th.apply_chart_theme(fig_cmp_vote, theme_mode), use_container_width=True)

        st.markdown("---")

    # Regular single-year overview
    sel_summary = summary[(summary["year"] == year) & summary["party"].isin(chosen_parties)]
    trend_summary = summary[summary["party"].isin(chosen_parties)]

    col_left, col_right = st.columns(2)
    with col_left:
        long_df = sel_summary.melt(
            id_vars="party",
            value_vars=["vote_share", "seat_share"],
            var_name="Metric",
            value_name="Percentage",
        )
        long_df["Metric"] = long_df["Metric"].map({"vote_share": "Vote Share (%)", "seat_share": "Seat Share (%)"})
        fig_bar = px.bar(
            long_df,
            x="party",
            y="Percentage",
            color="Metric",
            barmode="group",
            text_auto=".1f",
            title=f"Popular Vote Share vs Seat Share ({year})",
            color_discrete_map={"Vote Share (%)": "#00A3E0", "Seat Share (%)": "#FF9933"},
            labels={"party": "Party", "Percentage": "Share (%)"},
        )
        fig_bar = th.apply_chart_theme(fig_bar, theme_mode)
        fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        fig_trend = px.line(
            trend_summary,
            x="year",
            y="seat_vote_ratio",
            color="party",
            markers=True,
            title="Seat-to-Vote Ratio Over Time (1.0 = Proportional Parity)",
            labels={"seat_vote_ratio": "Seat / Vote Ratio", "year": "Election Year"},
            color_discrete_map={p: th.get_party_color(p) for p in chosen_parties},
        )
        fig_trend.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="#64748B",
            annotation_text="Parity (1.0)",
            annotation_position="bottom right",
        )
        fig_trend.update_xaxes(type="category")
        fig_trend = th.apply_chart_theme(fig_trend, theme_mode)
        fig_trend.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("📖 How to read the Vote Share vs Seat Share & Multiplier charts"):
        st.markdown(
            """
            - **Vote Share vs Seat Share**: Under First-Past-The-Post, geographically concentrated parties or national leaders
              consistently win a far higher proportion of seats than their popular vote share (the *manufactured majority* effect).
            - **Seat-to-Vote Ratio**: A ratio of **1.0** indicates exact proportional parity. Values **> 1.0** represent a seat bonus,
              while values **< 1.0** reflect an under-representation penalty.
            """
        )

    st.markdown("---")

    # Proportionality Scatter & Gallagher Gauge
    st.subheader("🎯 Electoral Parity Landscape & Disproportionality Gauge")
    scat_col, gauge_col = st.columns([1.4, 1.0])

    with scat_col:
        fig_scatter = th.build_proportionality_scatter(summary, year, parties=chosen_parties, theme_mode=theme_mode)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with gauge_col:
        avail = sorted(int(y) for y in summary["year"].unique())
        prev_yr = avail[avail.index(year) - 1] if year in avail and avail.index(year) > 0 else None
        prev_val = gi.get(prev_yr, None) if prev_yr else None
        fig_gauge = th.build_gallagher_gauge(float(gi.get(year, 0.0)), prev_val, theme_mode=theme_mode)
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.caption(
            "🟢 **0–6**: Highly proportional | 🟡 **6–13**: Moderate disproportionality | 🔴 **13+**: High majority bonus."
        )

    st.markdown("---")

    # Margins Histogram & Gallagher History
    st.subheader("⚡ Victory Margin Distribution & Gallagher Historical Progression")
    hist_col, gi_hist_col = st.columns(2)

    with hist_col:
        yr_margins = margins[margins["year"] == year]
        fig_hist = px.histogram(
            yr_margins,
            x="margin_pct",
            nbins=35,
            title=f"Winning Margin Distribution ({year})",
            labels={"margin_pct": "Victory Lead (% of Votes Cast)", "count": "Seats"},
            color_discrete_sequence=["#10B981"],
        )
        fig_hist.add_vline(
            x=threshold,
            line_dash="dash",
            line_color="#EF4444",
            annotation_text=f"Threshold ({threshold}%)",
            annotation_position="top right",
        )
        fig_hist = th.apply_chart_theme(fig_hist, theme_mode)
        st.plotly_chart(fig_hist, use_container_width=True)

    with gi_hist_col:
        gi_table = gi.reset_index()
        comp_map = completeness_df["missing"].to_dict() if not completeness_df.empty else {}
        gi_table["is_incomplete"] = gi_table["year"].map(lambda y: comp_map.get(y, 0) > 0)
        gi_table["display_year"] = gi_table.apply(
            lambda r: f"{r['year']}*" if r["is_incomplete"] else str(r["year"]), axis=1
        )
        gi_table["status"] = gi_table["is_incomplete"].map({
            True: "Indicative (Missing Data)",
            False: "Complete (543 Seats)",
        })

        fig_gi_trend = px.bar(
            gi_table,
            x="display_year",
            y="gallagher",
            text_auto=".1f",
            title="Gallagher Disproportionality Index Across General Elections",
            labels={"gallagher": "Gallagher Index", "display_year": "Election Year"},
            color="status",
            color_discrete_map={"Complete (543 Seats)": "#10B981", "Indicative (Missing Data)": "#FF9933"},
        )
        fig_gi_trend.update_xaxes(type="category")
        fig_gi_trend = th.apply_chart_theme(fig_gi_trend, theme_mode)
        fig_gi_trend.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_gi_trend, use_container_width=True)
        st.caption("* 2009 (541/543) and 2014 (511/543) have missing constituencies in source data; indices are indicative.")

    # Longitudinal Animation
    with st.expander("🎬 Longitudinal Animation: Vote vs Seat Share (2009–2024)", expanded=False):
        fig_anim = th.build_animated_vote_seat_bars(summary, chosen_parties, theme_mode=theme_mode)
        st.plotly_chart(fig_anim, use_container_width=True)


# ── TAB 2: Coalitions & Alliances ─────────────────────────────────────────────
def render_tab_coalitions(full_df: pd.DataFrame, year: int, theme_mode: str):
    """Renders Tab 2: Coalition dynamics, Parliament Hemicycle, and Sankey Diagram."""
    st.subheader(f"🤝 Major Coalition Dynamics & Seat Consolidation ({year})")
    st.info(
        "ℹ️ **Alliance Grouping Notice**: Coalition groupings (NDA, INDIA, UPA) are approximate pre-poll alignments "
        "loaded from `alliances.json`. Seat-sharing pacts vary across states, and specific partners contested independently "
        "in select states (e.g., AAP and INC in Punjab)."
    )

    alliance_df = e.alliance_summary(full_df, year)

    # Top row: Hemicycle + Coalition comparison
    hemi_col, bar_col = st.columns([1.1, 1.0])

    with hemi_col:
        fig_hemi = th.build_hemicycle_chart(alliance_df, year, theme_mode=theme_mode)
        st.plotly_chart(fig_hemi, use_container_width=True)

    with bar_col:
        alliance_long = alliance_df.melt(
            id_vars="alliance",
            value_vars=["vote_share", "seat_share"],
            var_name="Metric",
            value_name="Percentage",
        )
        alliance_long["Metric"] = alliance_long["Metric"].map({"vote_share": "Vote Share (%)", "seat_share": "Seat Share (%)"})
        fig_all_compare = px.bar(
            alliance_long,
            x="alliance",
            y="Percentage",
            color="Metric",
            barmode="group",
            text_auto=".1f",
            title=f"Coalition Vote Share vs Seat Share ({year})",
            labels={"alliance": "Coalition", "Percentage": "Share (%)"},
            color_discrete_map={"Vote Share (%)": "#00A3E0", "Seat Share (%)": "#FF9933"},
        )
        fig_all_compare = th.apply_chart_theme(fig_all_compare, theme_mode)
        fig_all_compare.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig_all_compare, use_container_width=True)

    st.markdown("---")

    # Sankey flow diagram
    st.subheader(f"🌊 Seat Allocation Flow: Political Parties ➔ Coalitions ({year})")
    fig_sankey = th.build_sankey_diagram(full_df, year, theme_mode=theme_mode)
    st.plotly_chart(fig_sankey, use_container_width=True)

    with st.expander("📖 How to read the Coalition Hemicycle & Sankey flow"):
        st.markdown(
            """
            - **Parliament Hemicycle**: Shows the 543 members of the Lok Sabha positioned as in a parliamentary chamber.
              The majority threshold needed to form a government is **272 seats**.
            - **Sankey Flow**: Traces how distinct state and national party seat tallies contribute directly to aggregate
              coalition strength (e.g. TDP and JD(U) into the NDA, or SP and DMK into the INDIA bloc).
            """
        )

    st.subheader(f"Coalition Breakdown ({year})")
    all_disp = alliance_df[["alliance", "votes", "seats", "vote_share", "seat_share", "seat_vote_ratio"]].copy()
    all_disp.columns = ["Alliance", "Total Votes", "Seats Won", "Vote Share (%)", "Seat Share (%)", "Seat/Vote Multiplier"]
    st.dataframe(all_disp.round(2), use_container_width=True, hide_index=True)


# ── TAB 3: State-by-State Footprint ───────────────────────────────────────────
def render_tab_states(full_df: pd.DataFrame, year: int, all_parties: list[str], theme_mode: str):
    """Renders Tab 3: State heatmap with grey NaNs and Gainers/Losers panel."""
    st.subheader("🗺️ Geographic & State-wise Electoral Footprint")

    party_for_state = st.selectbox(
        "Select Party for State Footprint Analysis:",
        all_parties,
        index=all_parties.index("BJP") if "BJP" in all_parties else 0,
    )

    state_data = e.state_party_summary(full_df, party_for_state)
    state_pivot = state_data.pivot(index="state", columns="year", values="vote_share").round(1)
    text_labels = state_pivot.map(lambda v: f"{v:.1f}%" if pd.notnull(v) else "No data")

    fig_heatmap = px.imshow(
        state_pivot,
        aspect="auto",
        color_continuous_scale="Viridis",
        labels=dict(x="Election Year", y="State / UT", color="Vote Share %"),
        title=f"{party_for_state} Vote Share by State (Grey = Missing in Source)",
    )
    fig_heatmap.update_traces(
        text=text_labels.values,
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>Year: %{x}<br>Vote Share: %{text}<extra></extra>",
    )
    fig_heatmap.update_layout(height=650, plot_bgcolor="#e5e7eb" if theme_mode == "light" else "#21262d")
    fig_heatmap = th.apply_chart_theme(fig_heatmap, theme_mode, height=650)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.caption("ℹ️ Grey cells indicate states where data was omitted in source files (e.g. Odisha and Chhattisgarh 2014).")

    st.markdown("---")

    # State Seats Won Bar Chart
    state_yr_df = state_data[state_data["year"] == year].sort_values("seats", ascending=False)
    st.subheader(f"{party_for_state} Seats Won by State ({year})")
    won_states = state_yr_df[state_yr_df["seats"] > 0]
    if not won_states.empty:
        fig_state_seats = px.bar(
            won_states,
            x="state",
            y="seats",
            text="seats",
            title=f"States where {party_for_state} Won Seats in {year}",
            labels={"state": "State", "seats": "Seats Won"},
            color_discrete_sequence=[th.get_party_color(party_for_state)],
        )
        fig_state_seats = th.apply_chart_theme(fig_state_seats, theme_mode)
        st.plotly_chart(fig_state_seats, use_container_width=True)
    else:
        st.info(f"{party_for_state} did not win any parliamentary seats in {year}.")


# ── TAB 4: Constituency Explorer ──────────────────────────────────────────────
def render_tab_constituencies(full_df: pd.DataFrame, margins: pd.DataFrame, year: int, theme_mode: str):
    """Renders Tab 4: Quick-picks, type-ahead search, Winner Spotlight Card, and Donut."""
    st.subheader("🔍 Constituency Deep Dive & Competitiveness Explorer")

    yr_constituencies = full_df[full_df["year"] == year]
    yr_margins = margins[margins["year"] == year]

    # Quick Picks
    st.markdown("##### ⚡ Quick-Pick Highlighted Contests")
    qp_col1, qp_col2 = st.columns(2)

    with qp_col1:
        st.caption("🔥 **Closest Contests (< 1% Margin)**")
        close_seats = yr_margins.sort_values("margin_pct").head(5)
        for _, r in close_seats.iterrows():
            btn_label = f"{r['cons']} ({r['state']}): {r['margin_pct']:.2f}% lead ({int(r['margin']):,} votes)"
            if st.button(btn_label, key=f"close_{r['cons']}_{year}"):
                st.session_state["selected_state"] = r["state"]
                st.session_state["selected_cons"] = r["cons"]

    with qp_col2:
        st.caption("🏔️ **Biggest Landslides (> 40% Margin)**")
        landslide_seats = yr_margins.sort_values("margin_pct", ascending=False).head(5)
        for _, r in landslide_seats.iterrows():
            btn_label = f"{r['cons']} ({r['state']}): {r['margin_pct']:.2f}% lead ({int(r['margin']):,} votes)"
            if st.button(btn_label, key=f"landslide_{r['cons']}_{year}"):
                st.session_state["selected_state"] = r["state"]
                st.session_state["selected_cons"] = r["cons"]

    st.markdown("---")

    # Selectors
    states_available = sorted(yr_constituencies["state"].unique())
    default_state = st.session_state.get("selected_state", states_available[0] if states_available else None)
    if default_state not in states_available and states_available:
        default_state = states_available[0]

    sc1, sc2 = st.columns(2)
    with sc1:
        sel_state = st.selectbox("Select State / UT:", states_available, index=states_available.index(default_state) if default_state else 0)

    cons_in_state = sorted(yr_constituencies[yr_constituencies["state"] == sel_state]["cons"].unique())
    default_cons = st.session_state.get("selected_cons", cons_in_state[0] if cons_in_state else None)
    if default_cons not in cons_in_state and cons_in_state:
        default_cons = cons_in_state[0]

    with sc2:
        sel_cons = st.selectbox("Select Parliamentary Constituency:", cons_in_state, index=cons_in_state.index(default_cons) if default_cons else 0)

    if sel_state and sel_cons:
        cons_df = yr_constituencies[
            (yr_constituencies["state"] == sel_state) & (yr_constituencies["cons"] == sel_cons)
        ].sort_values("position").reset_index(drop=True)

        cons_margin_info = yr_margins[
            (yr_margins["state"] == sel_state) & (yr_margins["cons"] == sel_cons)
        ]

        # Winner Card
        if not cons_df.empty:
            winner = cons_df.iloc[0]
            party_color = th.get_party_color(winner["party"])

            if not cons_margin_info.empty:
                m_row = cons_margin_info.iloc[0]
                margin_str = f"Won by <b>{int(m_row['margin']):,} votes</b> ({m_row['margin_pct']:.2f}% of votes polled)"
            elif year == 2024 and sel_cons.strip().upper() == "SURAT":
                margin_str = "Won unopposed (no polling held, margin N/A)"
            else:
                margin_str = "Margin data not available"

            st.markdown(
                f"""
                <div class="winner-card">
                    <div style="font-size:0.85rem; color:#888; font-weight:600; text-transform:uppercase;">Winner Spotlight</div>
                    <div class="winner-card-title">
                        {winner['candidate']}
                        <span class="party-chip" style="background-color:{party_color};">{winner['party']}</span>
                    </div>
                    <div style="font-size:0.95rem; color:#A0AEC0;">
                        {margin_str} | Total Valid Votes Cast: <b>{int(cons_df['votes'].sum()):,}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        cons_total = cons_df["votes"].sum()
        cons_df["Vote Share (%)"] = (cons_df["votes"] / cons_total * 100).round(2) if cons_total > 0 else 0.0

        # Donut Chart + Candidate Bar
        d_col1, d_col2 = st.columns([1.0, 1.2])
        with d_col1:
            fig_donut = th.build_constituency_donut(cons_df, theme_mode=theme_mode)
            st.plotly_chart(fig_donut, use_container_width=True)

        with d_col2:
            fig_cons = px.bar(
                cons_df.head(8),
                x="candidate",
                y="votes",
                color="party",
                text="votes",
                title=f"Leading Candidates in {sel_cons} ({sel_state}) — {year}",
                labels={"candidate": "Candidate", "votes": "Votes Polled", "party": "Party"},
                color_discrete_map={p: th.get_party_color(p) for p in cons_df["party"].unique()},
            )
            fig_cons = th.apply_chart_theme(fig_cons, theme_mode)
            st.plotly_chart(fig_cons, use_container_width=True)

        st.dataframe(
            cons_df[["position", "candidate", "party", "votes", "Vote Share (%)"]].rename(columns={"position": "Rank"}),
            use_container_width=True,
            hide_index=True,
        )


# ── TAB 5: Methodology & Clean Data Export ─────────────────────────────────────
def render_tab_methodology(
    full_df: pd.DataFrame,
    summary: pd.DataFrame,
    margins: pd.DataFrame,
    completeness_df: pd.DataFrame,
):
    """Renders Tab 5: Methodology, Delimitation Notice, Audit Table, and Clean Data Export."""
    st.subheader("📑 Methodology, Delimitation Rules & Data Audit")

    st.info(
        "ℹ️ **Delimitation & Boundary Notice**: The 2008 Delimitation order applies to the 2009, 2014, and 2019 "
        "general elections. In 2022, Jammu & Kashmir underwent delimitation (creating seats like Anantnag-Rajouri), "
        "Assam was reorganized under delimitation in 2023, and Ladakh became a separate Union Territory constituency in 2024. "
        "While aggregate national metrics remain valid, constituency-level longitudinal comparisons across these specific "
        "redrawn regions are not like-for-like."
    )

    st.subheader("📋 Dataset Completeness & Audit Summary")
    st.caption("Comparison of recorded constituencies versus the constitutional 543 Lok Sabha seats:")

    display_comp = completeness_df.reset_index().copy()
    display_comp["expected"] = e.EXPECTED_SEATS
    display_comp["status"] = display_comp["missing"].apply(
        lambda m: "✅ Complete (543 seats)" if m == 0 else f"⚠️ Indicative ({m} seats missing)"
    )
    display_comp.columns = ["Year", "Constituencies Present", "States / UTs Present", "Missing Seats", "Expected Seats", "Data Status"]
    display_comp = display_comp[["Year", "Constituencies Present", "Expected Seats", "Missing Seats", "States / UTs Present", "Data Status"]]
    st.dataframe(display_comp, use_container_width=True, hide_index=True)

    st.markdown(
        """
        ### Automated Cleaning Pipeline
        1. **Column Resolution**: Flexible column mapper recognizes official India Data Portal / ECI formats.
        2. **Party Normalization**: Resolves acronyms, coalition aliases, and spelling variations across 50+ major parties.
        3. **Candidate De-duplication**: De-duplicates candidate records per constituency and calculates candidate positions ($1, 2, \\dots$).
        4. **Uncontested Seats**: Accounts for unopposed seats (such as Surat 2024, won by BJP).
        5. **Metric Calculation**: Computes the Gallagher Disproportionality Index, victory margins, and seat-to-vote ratios.
        """
    )

    with st.expander("🔍 Top Unmapped Winning Parties (Inspect to Extend Party Normalization Dictionary)"):
        st.write("Winning parties in the dataset whose names are not yet aliased in `PARTY_ALIASES`:")
        unmapped_df = e.get_unmapped_winning_parties(full_df, top_n=30)
        if not unmapped_df.empty:
            st.dataframe(unmapped_df, use_container_width=True, hide_index=True)
        else:
            st.success("All winning parties are currently mapped in PARTY_ALIASES!")

    st.markdown("---")
    st.subheader("📥 Export Currently Processed Datasets")
    st.caption("Save cleaned metrics and candidate returns as standard CSV files:")

    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        st.download_button(
            label="💾 Download Party Summary (CSV)",
            data=summary.to_csv(index=False),
            file_name="processed_party_summary.csv",
            mime="text/csv",
            key="dl_btn_summary_csv",
            use_container_width=True,
        )
    with d_col2:
        st.download_button(
            label="💾 Download Margins Data (CSV)",
            data=margins.to_csv(index=False),
            file_name="processed_margins.csv",
            mime="text/csv",
            key="dl_btn_margins_csv",
            use_container_width=True,
        )
    with d_col3:
        st.download_button(
            label="💾 Download Full Candidates (CSV)",
            data=full_df.to_csv(index=False),
            file_name="processed_detailed_candidates.csv",
            mime="text/csv",
            key="dl_btn_candidates_csv",
            use_container_width=True,
        )

    st.markdown("##### 📁 Instant Local Disk Export")
    st.write("Save all three cleaned datasets directly to your local project folder:")
    export_dir = ROOT / "exports"
    if st.button("⚡ Save All 3 CSVs to 'exports/' Directory", key="btn_direct_disk_export"):
        export_dir.mkdir(parents=True, exist_ok=True)
        p_sum = export_dir / "party_summary.csv"
        p_mar = export_dir / "margins.csv"
        p_can = export_dir / "detailed_candidates.csv"

        summary.to_csv(p_sum, index=False)
        margins.to_csv(p_mar, index=False)
        full_df.to_csv(p_can, index=False)

        st.success(
            f"✅ **Export Successful!** All 3 datasets have been written directly to disk:\n\n"
            f"- `{p_sum.name}` ({len(summary):,} rows)\n"
            f"- `{p_mar.name}` ({len(margins):,} seats)\n"
            f"- `{p_can.name}` ({len(full_df):,} candidates)\n\n"
            f"Location: `{export_dir.resolve()}`"
        )


# ── Footer ────────────────────────────────────────────────────────────────────
def render_footer():
    """Renders the subtle application footer."""
    st.markdown(
        """
        <div class="app-footer">
            <b>Lok Sabha Election Analysis Application (2009–2024)</b><br>
            Data Sources: <i>Election Commission of India (ECI) & India Data Portal</i><br>
            Methodology: Gallagher Index of Disproportionality & First-Past-The-Post Electoral Analysis
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main Controller ───────────────────────────────────────────────────────────
def main():
    theme_mode = st.session_state.get("theme_mode", "dark")
    load_css(theme_mode)

    full_df, summary, margins, gi, cleaning_stats, theme_mode = render_sidebar(theme_mode)

    completeness_df = e.check_completeness(full_df)
    available_years = sorted(int(y) for y in summary["year"].unique())

    # Sidebar: Compare Elections Toggle
    st.sidebar.subheader("🎛️ Analysis Controls")
    is_compare_mode = st.sidebar.checkbox("⚖️ Compare Two Elections Side-by-Side", value=False)
    compare_years = []

    if is_compare_mode and len(available_years) >= 2:
        cy1 = st.sidebar.selectbox("Baseline Year:", available_years, index=len(available_years) - 2)
        cy2 = st.sidebar.selectbox("Comparison Year:", available_years, index=len(available_years) - 1)
        compare_years = [cy1, cy2]
        active_year = cy2
    else:
        # Timeline Slider with optional Auto-Play
        st.sidebar.markdown("**📅 Election Year Timeline:**")
        active_year = st.sidebar.select_slider(
            "Select Election Year:",
            options=available_years,
            value=available_years[-1] if available_years else 2024,
        )

        # Auto-play button
        if st.sidebar.button("▶️ Play Timeline Animation"):
            for step_yr in available_years:
                st.session_state["selected_year"] = step_yr
                time.sleep(0.8)
            st.rerun()

    all_parties = sorted(summary["party"].unique())
    popular = ["BJP", "INC", "AITC", "SP", "DMK", "AAP", "TDP", "JD(U)"]
    default_parties = [p for p in popular if p in all_parties] or all_parties[:4]

    chosen_parties = st.sidebar.multiselect(
        "🎯 Select Parties to Compare:",
        all_parties,
        default=default_parties,
    )

    threshold = st.sidebar.slider(
        "⚡ Competitive Seat Lead Threshold (% Margin)",
        min_value=1.0,
        max_value=15.0,
        value=5.0,
        step=0.5,
    )

    # Ingestion cleaning report banner
    if cleaning_stats:
        with st.expander("🛠️ Raw Data Auto-Cleaning Summary & Ingestion Report", expanded=False):
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Raw Rows Ingested", f"{cleaning_stats['raw_rows']:,}")
            sc2.metric("Cleaned Candidates", f"{cleaning_stats['cleaned_rows']:,}")
            sc3.metric("Constituencies Validated", f"{cleaning_stats['constituencies']:,}")
            sc4.metric("Duplicates Dropped", f"{cleaning_stats['duplicates_removed']:,}")

    # Top Hero Header
    render_hero_header(active_year, is_compare_mode, compare_years)

    # Completeness Warning for currently selected year
    if active_year in completeness_df.index:
        yr_comp = completeness_df.loc[active_year]
        missing_seats = int(yr_comp["missing"])
        present_seats = int(yr_comp["constituencies"])
        if missing_seats > 0:
            st.warning(
                f"⚠️ **Data Completeness Warning ({active_year})**: Only {present_seats}/{e.EXPECTED_SEATS} constituencies "
                f"present ({missing_seats} missing in source files). Seat shares and the Gallagher index for this year "
                f"are indicative only."
            )

    # Surat 2024 Note
    if active_year == 2024:
        st.info(
            "💡 **Surat 2024 Unopposed Seat Note**: In 2024, the BJP candidate won Surat (Gujarat) unopposed without polling. "
            "The victory margins dataset contains 542 seats in 2024 because there was no runner-up candidate to compute a margin against."
        )

    # KPI Metrics
    render_kpis(margins, summary, gi, active_year, threshold)

    # AI Plain-English Insights Panel
    render_insights_panel(summary, margins, gi, active_year)

    # Main Pill Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 National Overview & Proportionality",
        "🤝 Coalitions & Alliances",
        "🗺️ State-by-State Footprint",
        "🔍 Constituency Explorer",
        "📑 Methodology & Clean Data Export",
    ])

    with tab1:
        render_tab_national(
            summary, margins, gi, active_year, chosen_parties, threshold, completeness_df, theme_mode, is_compare_mode, compare_years
        )

    with tab2:
        render_tab_coalitions(full_df, active_year, theme_mode)

    with tab3:
        render_tab_states(full_df, active_year, all_parties, theme_mode)

    with tab4:
        render_tab_constituencies(full_df, margins, active_year, theme_mode)

    with tab5:
        render_tab_methodology(full_df, summary, margins, completeness_df)

    render_footer()


if __name__ == "__main__":
    main()
