"""Cleaning and metrics for the Lok Sabha vote-share vs seat-share analysis.

Input: the India Data Portal "Constituency Wise Detailed Results" CSVs
(2004-2014 and 2019-2024 files, or the combined file made by download_data.py).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Seats expected in each general election (2019: Vellore was countermanded, then polled later).
EXPECTED_SEATS = 543

# ---- 1. Party-name normalisation -----------------------------------------
# Keys are upper-case with single spaces. Extend after checking
# df[df.position == 1].party.value_counts() for unmapped long names.
PARTY_ALIASES = {
    "BHARATIYA JANATA PARTY": "BJP",
    "INDIAN NATIONAL CONGRESS": "INC",
    "ALL INDIA TRINAMOOL CONGRESS": "AITC",
    "SAMAJWADI PARTY": "SP",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "DRAVIDA MUNNETRA KAZHAGAM": "DMK",
    "ALL INDIA ANNA DRAVIDA MUNNETRA KAZHAGAM": "AIADMK",
    "SHIVSENA": "SHS",
    "SHIV SENA": "SHS",
    "SHIV SENA (UDDHAV BALASAHEB THACKREY)": "SHSUBT",
    "TELUGU DESAM": "TDP",
    "TELUGU DESAM PARTY": "TDP",
    "YUVAJANA SRAMIKA RYTHU CONGRESS PARTY": "YSRCP",
    "JANATA DAL (UNITED)": "JD(U)",
    "JANATA DAL (SECULAR)": "JD(S)",
    "COMMUNIST PARTY OF INDIA (MARXIST)": "CPI(M)",
    "COMMUNIST PARTY OF INDIA": "CPI",
    "BIJU JANATA DAL": "BJD",
    "TELANGANA RASHTRA SAMITHI": "TRS",
    "NATIONALIST CONGRESS PARTY": "NCP",
    "NATIONALIST CONGRESS PARTY \u2013 SHARADCHANDRA PAWAR": "NCP(SP)",
    "RASHTRIYA JANATA DAL": "RJD",
    "LOK JAN SHAKTI PARTY": "LJP",
    "LOK JANSHAKTI PARTY(RAM VILAS)": "LJP(RV)",
    "SHIROMANI AKALI DAL": "SAD",
    "JAMMU & KASHMIR NATIONAL CONFERENCE": "JKNC",
    "JHARKHAND MUKTI MORCHA": "JMM",
    "INDIAN UNION MUSLIM LEAGUE": "IUML",
    "AAM AADMI PARTY": "AAP",
    "RASHTRIYA LOK DAL": "RLD",
    "ALL INDIA MAJLIS-E-ITTEHADUL MUSLIMEEN": "AIMIM",
    "REVOLUTIONARY SOCIALIST PARTY": "RSP",
    "INDEPENDENT": "IND",
}


def normalise_party(s: pd.Series) -> pd.Series:
    cleaned = s.astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True)
    # tidy "(  X )" style gaps left over from the source, then map
    cleaned = cleaned.str.replace(r"\(\s+", "(", regex=True).str.replace(r"\s+\)", ")", regex=True)
    mapped = cleaned.replace(PARTY_ALIASES)
    return mapped


# ---- 2. Loading & Cleaning Engine ---------------------------------------
def load_lok_sabha(
    path_or_df,
    start: int = 2000,
    end: int = 2030,
    add_unopposed: bool = True,
    supplements: list[str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Load and clean election CSVs (from file paths, uploaded file buffers, or DataFrames).

    Standardizes columns, normalizes party aliases, deduplicates candidate records,
    computes within-constituency candidate positions, and handles uncontested seats.

    Returns:
        tuple[pd.DataFrame, dict]: Cleaned candidate DataFrame and a dictionary of cleaning statistics.
    """
    if isinstance(path_or_df, pd.DataFrame):
        raw = path_or_df.copy()
    else:
        paths = [path_or_df] if not isinstance(path_or_df, list) else path_or_df
        paths = paths + list(supplements or [])
        raw_list = []
        for p in paths:
            if isinstance(p, pd.DataFrame):
                raw_list.append(p)
            else:
                raw_list.append(pd.read_csv(p, low_memory=False))
        raw = pd.concat(raw_list, ignore_index=True)

    initial_row_count = len(raw)

    # Standardize column names (strip whitespace and lower-case lookup)
    col_map = {str(c).strip().lower(): c for c in raw.columns}

    def _get_col(*candidates: str) -> str | None:
        for c in candidates:
            if c.lower() in col_map:
                return col_map[c.lower()]
        return None

    year_col = _get_col("year")
    state_col = _get_col("state_name", "state", "statename")
    pc_col = _get_col("pc_name", "pcname", "constituency", "constituency_name", "cons")
    party_col = _get_col("party_name", "party", "partyname")

    if not all([year_col, state_col, pc_col, party_col]):
        missing = [
            req
            for req, found in [
                ("year", year_col),
                ("state_name", state_col),
                ("pc_name", pc_col),
                ("party_name", party_col),
            ]
            if found is None
        ]
        raise KeyError(f"Required column(s) not found in uploaded file: {missing}")

    cand_col = _get_col("candidate_name", "candidate", "candidatename")
    gen_votes_col = _get_col("votes_secured_general")
    post_votes_col = _get_col("votes_secured_postal")
    tot_votes_col = _get_col("votes", "total_votes", "valid_votes")
    electors_col = _get_col("total_electors", "electors", "totalelectors")

    # Compute votes per candidate
    if gen_votes_col and post_votes_col:
        votes_series = (
            pd.to_numeric(raw[gen_votes_col], errors="coerce").fillna(0)
            + pd.to_numeric(raw[post_votes_col], errors="coerce").fillna(0)
        )
    elif gen_votes_col:
        votes_series = pd.to_numeric(raw[gen_votes_col], errors="coerce").fillna(0)
    elif tot_votes_col:
        votes_series = pd.to_numeric(raw[tot_votes_col], errors="coerce").fillna(0)
    else:
        votes_series = pd.Series(0, index=raw.index)

    candidate_series = raw[cand_col].astype(str).str.strip() if cand_col else pd.Series("Unknown", index=raw.index)
    electors_series = pd.to_numeric(raw[electors_col], errors="coerce") if electors_col else pd.Series(np.nan, index=raw.index)

    df = pd.DataFrame({
        "year": pd.to_numeric(raw[year_col], errors="coerce").fillna(0).astype(int),
        "state": raw[state_col].astype(str).str.strip(),
        "cons": raw[pc_col].astype(str).str.strip(),
        "candidate": candidate_series,
        "party": normalise_party(raw[party_col]),
        "votes": votes_series,
        "electors": electors_series,
    })

    # Filter year range and deduplicate on candidate identity
    df = df[df["year"].between(start, end)].drop_duplicates(
        subset=["year", "state", "cons", "candidate", "party"]
    ).copy()
    df["cons_id"] = df["state"] + "|" + df["cons"]

    # Rank candidates by total votes inside each constituency
    df["position"] = (
        df.groupby(["year", "cons_id"])["votes"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    unopposed_added = False
    if add_unopposed and 2024 in df["year"].values and start <= 2024 <= end:
        before_len = len(df)
        df = _add_surat_2024(df)
        unopposed_added = len(df) > before_len

    df = df.reset_index(drop=True)

    cleaning_stats = {
        "raw_rows": initial_row_count,
        "cleaned_rows": len(df),
        "duplicates_removed": max(0, initial_row_count - len(df)),
        "constituencies": int(df["cons_id"].nunique()),
        "years": sorted(int(y) for y in df["year"].unique()),
        "states_count": int(df["state"].nunique()),
        "parties_count": int(df["party"].nunique()),
        "unopposed_handled": unopposed_added,
    }

    return df, cleaning_stats


def process_election_data(
    source,
    start: int = 2000,
    end: int = 2030,
    add_unopposed: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, dict]:
    """End-to-end cleaning and analytical metrics pipeline.

    Takes raw data (file path, file buffer, or DataFrame), standardizes it,
    computes national party summaries, constituency margins, and Gallagher index.

    Returns:
        (clean_df, party_summary_df, margins_df, gallagher_index_series, cleaning_stats)
    """
    clean_df, stats = load_lok_sabha(source, start=start, end=end, add_unopposed=add_unopposed)
    summary_df = party_summary(clean_df)
    margins_df = constituency_margins(clean_df)
    gi_series = gallagher_index(summary_df)
    return clean_df, summary_df, margins_df, gi_series, stats


def _add_surat_2024(df: pd.DataFrame) -> pd.DataFrame:
    """Surat (Gujarat) 2024: BJP won unopposed, so the source file has no rows for it.
    Adds one winner row with 0 votes so the seat is counted; vote shares are unaffected.
    The check is case-insensitive to match whatever the CSV spells the name as.
    """
    already_present = (
        (df["year"] == 2024)
        & (df["cons"].str.upper() == "SURAT")
    ).any()
    if already_present:
        return df
    row = pd.DataFrame([{
        "year": 2024, "state": "Gujarat", "cons": "Surat", "candidate": "Unopposed",
        "party": "BJP", "votes": 0, "electors": np.nan, "cons_id": "Gujarat|Surat", "position": 1,
    }])
    return pd.concat([df, row], ignore_index=True)


def check_completeness(df: pd.DataFrame, expected: int = EXPECTED_SEATS) -> pd.DataFrame:
    """Constituencies and states present per year. Anything short of `expected` needs patching
    before national totals can be trusted."""
    out = df.groupby("year").agg(constituencies=("cons_id", "nunique"), states=("state", "nunique"))
    out["missing"] = expected - out["constituencies"]
    return out


def get_unmapped_winning_parties(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    """Lists the top unmapped winning party names per year and the seats they won.

    Assists researchers in identifying party names that won parliamentary
    seats but do not currently exist in PARTY_ALIASES.
    """
    known_aliases = set(PARTY_ALIASES.values())
    winners = df[df["position"] == 1].copy()
    unmapped = winners[~winners["party"].isin(known_aliases)]
    if unmapped.empty:
        return pd.DataFrame(columns=["year", "party", "seats_won"])

    counts = (
        unmapped.groupby(["year", "party"])
        .size()
        .rename("seats_won")
        .reset_index()
        .sort_values(["year", "seats_won", "party"], ascending=[True, False, True])
    )
    return counts.groupby("year").head(top_n).reset_index(drop=True)


# ---- 4. Core metrics -----------------------------------------------------
def party_summary(df: pd.DataFrame) -> pd.DataFrame:
    """National seats, votes, vote share, seat share per party per year."""
    winners = df[df["position"] == 1]
    seats = winners.groupby(["year", "party"]).size().rename("seats")
    votes = df.groupby(["year", "party"])["votes"].sum().rename("votes")
    out = pd.concat([votes, seats], axis=1).fillna({"seats": 0}).reset_index()
    out["seats"] = out["seats"].astype(int)

    out["vote_share"] = out["votes"] / out.groupby("year")["votes"].transform("sum") * 100
    out["seat_share"] = out["seats"] / out.groupby("year")["seats"].transform("sum") * 100
    # Guard against division-by-zero when a party has 0 vote share (e.g. unopposed row)
    out["seat_vote_ratio"] = np.where(
        out["vote_share"] > 0,
        out["seat_share"] / out["vote_share"],
        np.nan,
    )
    return out.sort_values(["year", "seats"], ascending=[True, False]).reset_index(drop=True)


def gallagher_index(summary: pd.DataFrame) -> pd.Series:
    """Gallagher least-squares disproportionality per year (0 = perfectly proportional).

    Uses every party, so pass the full party_summary, not a trimmed one.
    """
    def _g(g: pd.DataFrame) -> float:
        return float(np.sqrt(0.5 * ((g["vote_share"] - g["seat_share"]) ** 2).sum()))

    # pandas ≥ 2.2 requires include_groups=False; the fallback handles older versions.
    try:
        return summary.groupby("year").apply(_g, include_groups=False).rename("gallagher")
    except TypeError:  # pandas < 2.2
        return summary.groupby("year").apply(_g).rename("gallagher")


def constituency_margins(df: pd.DataFrame) -> pd.DataFrame:
    """Winner's margin over runner-up, in votes and as % of votes cast.

    Constituencies with only one candidate (e.g. Surat 2024, unopposed) are
    excluded because there is no runner-up to compute a margin against.
    """
    top2 = df[df["position"].isin([1, 2])].pivot_table(
        index=["year", "state", "cons_id", "cons"],
        columns="position", values="votes", aggfunc="max",
    )
    # Flatten the MultiIndex columns that pivot_table produces (integers 1 and 2).
    top2.columns = [int(c) for c in top2.columns]
    # Drop constituencies that have no runner-up (unopposed seats).
    top2 = top2.dropna(subset=[2])
    top2 = top2.rename(columns={1: "winner_votes", 2: "runner_up_votes"})

    total = df.groupby(["year", "cons_id"])["votes"].sum().rename("total_votes")
    m = top2.reset_index().merge(total, on=["year", "cons_id"])
    m["margin"] = m["winner_votes"] - m["runner_up_votes"]
    m["margin_pct"] = m["margin"] / m["total_votes"] * 100
    return m


def competitive_share(margins: pd.DataFrame, threshold_pct: float = 5.0) -> pd.DataFrame:
    """Share of seats decided by less than `threshold_pct` of votes cast."""
    g = margins.groupby("year")["margin_pct"]
    return pd.DataFrame({
        "seats": g.size(),
        "close_seats": g.apply(lambda s: (s < threshold_pct).sum()),
    }).assign(close_share=lambda d: d["close_seats"] / d["seats"] * 100).reset_index()


def state_party_summary(df: pd.DataFrame, party: str) -> pd.DataFrame:
    """Per state and year: one party's vote share and seats won."""
    d = df.copy()
    d["is_party"] = d["party"] == party

    def _vote_share(g: pd.DataFrame) -> float:
        total = g["votes"].sum()
        return g.loc[g["is_party"], "votes"].sum() / total * 100 if total > 0 else 0.0

    try:
        votes = d.groupby(["year", "state"]).apply(_vote_share, include_groups=False).rename("vote_share")
    except TypeError:  # pandas < 2.2
        votes = d.groupby(["year", "state"]).apply(_vote_share).rename("vote_share")

    seats = d[(d["position"] == 1) & d["is_party"]].groupby(["year", "state"]).size().rename("seats")
    out = pd.concat([votes, seats], axis=1).fillna({"seats": 0}).reset_index()
    out["seats"] = out["seats"].astype(int)
    return out


# ---- 5. Alliance & Coalition Helpers -------------------------------------
DEFAULT_ALLIANCES: dict[int, dict[str, list[str]]] = {
    2024: {
        "NDA": ["BJP", "JD(U)", "TDP", "SHS", "LJP(RV)", "JD(S)", "RLD", "JSP", "AGP", "HAM", "SKM", "ADAL"],
        "INDIA": ["INC", "SP", "AITC", "DMK", "SHSUBT", "NCP(SP)", "CPI(M)", "RJD", "AAP", "CPI", "JMM", "IUML", "JKNC", "VCK"],
    },
    2019: {
        "NDA": ["BJP", "SHS", "JD(U)", "LJP", "SAD", "ADAL", "AGP", "AJSU", "NDPP"],
        "UPA": ["INC", "DMK", "NCP", "IUML", "JKNC", "JMM", "RJD", "JD(S)"],
    },
    2014: {
        "NDA": ["BJP", "SHS", "TDP", "LJP", "SAD", "RLSP", "ADAL", "SWP", "PMK"],
        "UPA": ["INC", "NCP", "RJD", "JMM", "IUML", "KEC(M)"],
    },
    2009: {
        "UPA": ["INC", "DMK", "AITC", "NCP", "JKNC", "IUML", "JMM"],
        "NDA": ["BJP", "JD(U)", "SHS", "SAD", "RLD", "AGP"],
    },
}


def load_alliances(file_path: Path | str | None = None) -> dict[int, dict[str, list[str]]]:
    """Loads political alliances from alliances.json with graceful fallback to defaults."""
    search_paths = []
    if file_path:
        search_paths.append(Path(file_path))
    search_paths.extend([
        Path("alliances.json"),
        Path(__file__).resolve().parent / "alliances.json",
        Path(__file__).resolve().parents[1] / "alliances.json",
    ])
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        search_paths.append(Path(sys._MEIPASS) / "alliances.json")

    for p in search_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return {int(year): data for year, data in raw.items()}
            except Exception as ex:
                warnings.warn(f"Failed to load alliances from {p}: {ex}. Using default alliances.")
                break

    return DEFAULT_ALLIANCES


ALLIANCES = load_alliances()


def get_alliance_map(year: int) -> dict[str, str]:
    """Returns mapping from party name to alliance string (e.g. 'NDA', 'INDIA', 'UPA') for a given election year."""
    global ALLIANCES
    year_map = ALLIANCES.get(year, {})
    mapping = {}
    for alliance_name, party_list in year_map.items():
        for party in party_list:
            mapping[party] = alliance_name
    return mapping


def alliance_summary(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Computes aggregated seats, votes, vote share, and seat share by major political alliance."""
    d = df[df["year"] == year].copy()
    mapping = get_alliance_map(year)
    d["alliance"] = d["party"].map(mapping).fillna("Others")

    winners = d[d["position"] == 1]
    seats = winners.groupby("alliance").size().rename("seats")
    votes = d.groupby("alliance")["votes"].sum().rename("votes")
    out = pd.concat([votes, seats], axis=1).fillna({"seats": 0}).reset_index()
    out["seats"] = out["seats"].astype(int)

    total_votes = out["votes"].sum()
    total_seats = out["seats"].sum()
    out["vote_share"] = (out["votes"] / total_votes * 100) if total_votes > 0 else 0
    out["seat_share"] = (out["seats"] / total_seats * 100) if total_seats > 0 else 0
    out["seat_vote_ratio"] = np.where(out["vote_share"] > 0, out["seat_share"] / out["vote_share"], np.nan)
    return out.sort_values("seats", ascending=False).reset_index(drop=True)


def headline_table(summary: pd.DataFrame, parties=("BJP", "INC")) -> pd.DataFrame:
    """Tidy table for the report and slides: the major parties side by side."""
    t = summary[summary["party"].isin(parties)].copy()
    return t[["year", "party", "seats", "vote_share", "seat_share", "seat_vote_ratio"]].round(2)


