"""Unit tests for elections metrics and cleaning engine.

These tests use tiny hand-crafted DataFrames with known mathematical solutions
so that results can be verified by hand for viva and grading evaluation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure src is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import elections as e


@pytest.fixture
def sample_election_df() -> pd.DataFrame:
    """Creates a tiny 2-constituency, 2-party mock election for 2024.

    Constituency 1 (State 1 | Cons 1):
      - Party A: 60 votes (Position 1, Winner)
      - Party B: 40 votes (Position 2)
      Total valid votes = 100

    Constituency 2 (State 1 | Cons 2):
      - Party A: 45 votes (Position 2)
      - Party B: 55 votes (Position 1, Winner)
      Total valid votes = 100

    National Totals:
      - Total votes = 200
      - Total seats = 2
      - Party A: 105 votes (52.5%), 1 seat (50.0%)
      - Party B: 95 votes (47.5%), 1 seat (50.0%)
    """
    return pd.DataFrame([
        {"year": 2024, "state": "State 1", "cons": "Cons 1", "cons_id": "State 1|Cons 1", "candidate": "Alice", "party": "Party A", "votes": 60, "electors": 120, "position": 1},
        {"year": 2024, "state": "State 1", "cons": "Cons 1", "cons_id": "State 1|Cons 1", "candidate": "Bob", "party": "Party B", "votes": 40, "electors": 120, "position": 2},
        {"year": 2024, "state": "State 1", "cons": "Cons 2", "cons_id": "State 1|Cons 2", "candidate": "Charlie", "party": "Party A", "votes": 45, "electors": 130, "position": 2},
        {"year": 2024, "state": "State 1", "cons": "Cons 2", "cons_id": "State 1|Cons 2", "candidate": "Diana", "party": "Party B", "votes": 55, "electors": 130, "position": 1},
    ])


def test_party_summary(sample_election_df: pd.DataFrame):
    """Verifies seats, vote shares, seat shares, and seat-to-vote ratios."""
    summary = e.party_summary(sample_election_df)

    party_a = summary[summary["party"] == "Party A"].iloc[0]
    party_b = summary[summary["party"] == "Party B"].iloc[0]

    # Verify seats won (1 seat each)
    assert party_a["seats"] == 1
    assert party_b["seats"] == 1

    # Verify total votes (105 and 95 out of 200)
    assert party_a["votes"] == 105
    assert party_b["votes"] == 95

    # Verify vote shares: 105/200 = 52.5%, 95/200 = 47.5%
    assert pytest.approx(party_a["vote_share"], rel=1e-4) == 52.5
    assert pytest.approx(party_b["vote_share"], rel=1e-4) == 47.5

    # Verify seat shares: 1/2 = 50.0% each
    assert pytest.approx(party_a["seat_share"], rel=1e-4) == 50.0
    assert pytest.approx(party_b["seat_share"], rel=1e-4) == 50.0

    # Verify seat-to-vote ratios:
    # Party A: 50.0 / 52.5 = 0.95238
    # Party B: 50.0 / 47.5 = 1.05263
    assert pytest.approx(party_a["seat_vote_ratio"], rel=1e-4) == 50.0 / 52.5
    assert pytest.approx(party_b["seat_vote_ratio"], rel=1e-4) == 50.0 / 47.5


def test_gallagher_index(sample_election_df: pd.DataFrame):
    """Verifies Gallagher Index least-squares calculation by hand.

    Formula: sqrt( 0.5 * sum( (VoteShare - SeatShare)^2 ) )
    Party A: (52.5 - 50.0)^2 = 2.5^2 = 6.25
    Party B: (47.5 - 50.0)^2 = (-2.5)^2 = 6.25
    Sum of squares = 6.25 + 6.25 = 12.50
    Half sum = 6.25
    sqrt(6.25) = exactly 2.50
    """
    summary = e.party_summary(sample_election_df)
    gi = e.gallagher_index(summary)

    assert 2024 in gi.index
    assert pytest.approx(gi.loc[2024], rel=1e-4) == 2.50


def test_constituency_margins(sample_election_df: pd.DataFrame):
    """Verifies winner lead in votes and victory margin percentage.

    Cons 1:
      Winner: Alice (60 votes), Runner-up: Bob (40 votes)
      Margin in votes = 60 - 40 = 20 votes
      Margin % = 20 / 100 * 100 = 20.0%

    Cons 2:
      Winner: Diana (55 votes), Runner-up: Charlie (45 votes)
      Margin in votes = 55 - 45 = 10 votes
      Margin % = 10 / 100 * 100 = 10.0%
    """
    margins = e.constituency_margins(sample_election_df)
    assert len(margins) == 2

    c1 = margins[margins["cons"] == "Cons 1"].iloc[0]
    assert c1["margin"] == 20
    assert pytest.approx(c1["margin_pct"], rel=1e-4) == 20.0

    c2 = margins[margins["cons"] == "Cons 2"].iloc[0]
    assert c2["margin"] == 10
    assert pytest.approx(c2["margin_pct"], rel=1e-4) == 10.0


def test_unopposed_seat_margins_exclusion(sample_election_df: pd.DataFrame):
    """Surat / Uncontested seats test:
    When a seat is won unopposed (1 candidate, position 1, no runner-up),
    it must be excluded from constituency_margins without raising an error.
    """
    unopposed_row = pd.DataFrame([{
        "year": 2024,
        "state": "State 1",
        "cons": "Cons 3",
        "cons_id": "State 1|Cons 3",
        "candidate": "Unopposed Winner",
        "party": "Party C",
        "votes": 0,
        "electors": 100,
        "position": 1,
    }])
    df_with_unopposed = pd.concat([sample_election_df, unopposed_row], ignore_index=True)

    # In constituency_margins, Cons 3 has no position 2 (runner-up), so only 2 seats returned
    margins = e.constituency_margins(df_with_unopposed)
    assert len(margins) == 2
    assert "Cons 3" not in margins["cons"].values

    # In check_completeness, 3 constituencies are registered
    comp = e.check_completeness(df_with_unopposed, expected=5)
    assert comp.loc[2024, "constituencies"] == 3
    assert comp.loc[2024, "missing"] == 2
