"""Theme system, color palettes, and custom Plotly visual builders.

Provides:
- Consistent political party & alliance color palettes
- Dark & Light custom Plotly layout templates
- Interactive chart builders:
  - Gallagher Index Gauge with risk bands
  - Semicircle Parliament Hemicycle for Lok Sabha seat counts
  - Party -> Alliance -> Seats Sankey flow
  - Vote Share vs Seat Share Proportionality Scatter
  - Longitudinal Animated Bar Chart
  - Candidate Vote-Share Donut
  - State-level Gainers & Losers Bar
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── 1. Party & Alliance Color Palettes ────────────────────────────────────────
PARTY_COLORS: dict[str, str] = {
    "BJP": "#FF9933",       # Saffron
    "INC": "#00A3E0",       # Sky / Congress Blue
    "AITC": "#20BF55",      # Trinamool Green
    "SP": "#E53935",        # Samajwadi Red
    "DMK": "#D32F2F",       # DMK Red
    "AIADMK": "#2E7D32",    # AIADMK Green
    "AAP": "#00897B",       # AAP Teal
    "TDP": "#FBC02D",       # TDP Yellow
    "JD(U)": "#388E3C",     # JD(U) Green
    "JD(S)": "#1B5E20",     # JD(S) Forest Green
    "SHS": "#FB8C00",       # Shiv Sena Orange
    "SHSUBT": "#F57C00",    # Shiv Sena (UBT)
    "YSRCP": "#1976D2",     # YSRCP Royal Blue
    "CPI(M)": "#C62828",    # CPI(M) Crimson
    "CPI": "#D32F2F",       # CPI Red
    "BJD": "#00796B",       # BJD Greenish Teal
    "TRS": "#EC407A",       # TRS Pink
    "NCP": "#0288D1",       # NCP Cyan Blue
    "NCP(SP)": "#039BE5",   # NCP (Sharadchandra Pawar)
    "RJD": "#2E7D32",       # RJD Green
    "BSP": "#1E88E5",       # BSP Blue
    "LJP": "#795548",       # LJP Brown
    "LJP(RV)": "#8D6E63",   # LJP (Ram Vilas)
    "SAD": "#FFB300",       # Akali Dal Amber
    "JKNC": "#C62828",      # JKNC Red
    "JMM": "#2E7D32",       # JMM Green
    "IUML": "#388E3C",      # IUML Green
    "AIMIM": "#004D40",     # AIMIM Deep Green
    "RLD": "#43A047",       # RLD Green
    "IND": "#78909C",       # Independent Grey
    "OTHERS": "#9E9E9E",    # Neutral Grey
}

ALLIANCE_COLORS: dict[str, str] = {
    "NDA": "#FF9933",       # Saffron
    "INDIA": "#138808",     # Emerald Green
    "UPA": "#1565C0",       # UPA Blue
    "Others": "#78909C",    # Neutral Grey
}


def get_party_color(party: str) -> str:
    """Returns official hexadecimal color for a party with a sensible fallback."""
    return PARTY_COLORS.get(party.strip().upper(), "#78909C")


def get_alliance_color(alliance: str) -> str:
    """Returns official hexadecimal color for an alliance."""
    return ALLIANCE_COLORS.get(alliance.strip(), "#78909C")


# ── 2. Custom Plotly Layout Theming ──
def get_plotly_template(theme_mode: str = "dark") -> dict:
    """Returns a polished Plotly layout dictionary based on active theme."""
    is_dark = theme_mode.lower() == "dark"

    bg_color = "rgba(0, 0, 0, 0)"
    font_color = "#F0F6FC" if is_dark else "#0F172A"
    grid_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.07)"
    card_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.1)"

    return dict(
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif", color=font_color, size=12),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=45, r=25, t=55, b=45),
        hoverlabel=dict(
            bgcolor="#1E2530" if is_dark else "#FFFFFF",
            font_color=font_color,
            font_size=12,
            bordercolor=card_border,
        ),
        xaxis=dict(
            gridcolor=grid_color,
            zerolinecolor=grid_color,
            tickfont=dict(color=font_color),
            title_font=dict(color=font_color, size=12),
        ),
        yaxis=dict(
            gridcolor=grid_color,
            zerolinecolor=grid_color,
            tickfont=dict(color=font_color),
            title_font=dict(color=font_color, size=12),
        ),
        legend=dict(
            font=dict(color=font_color),
            bgcolor="rgba(0,0,0,0)",
        ),
    )


def apply_chart_theme(fig, theme_mode: str = "dark", height: int | None = None) -> go.Figure:
    """Applies the custom theme and download image config to any Plotly figure."""
    tpl = get_plotly_template(theme_mode)
    fig.update_layout(
        font=tpl["font"],
        paper_bgcolor=tpl["paper_bgcolor"],
        plot_bgcolor=tpl["plot_bgcolor"],
        hoverlabel=tpl["hoverlabel"],
        legend=tpl["legend"],
        xaxis=tpl["xaxis"],
        yaxis=tpl["yaxis"],
    )
    if height:
        fig.update_layout(height=height)
    return fig


# ── 3. Gallagher Index Gauge Chart ──
def build_gallagher_gauge(current_val: float, prev_val: float | None = None, theme_mode: str = "dark") -> go.Figure:
    """Renders a modern gauge chart for the Gallagher Disproportionality Index with interpretation bands."""
    is_dark = theme_mode.lower() == "dark"
    font_color = "#F0F6FC" if is_dark else "#0F172A"

    delta_dict = None
    if prev_val is not None and not np.isnan(prev_val):
        delta_dict = {
            "reference": prev_val,
            "increasing": {"color": "#EF4444"},  # higher disproportionality is worse
            "decreasing": {"color": "#10B981"},  # lower is more proportional
            "valueformat": ".1f",
        }

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number" + ("+delta" if delta_dict else ""),
            value=current_val,
            delta=delta_dict,
            number={"valueformat": ".1f", "font": {"size": 42, "color": font_color, "family": "Inter"}},
            title={"text": "Gallagher Disproportionality Index (0 = Parity)", "font": {"size": 15, "color": font_color}},
            gauge={
                "axis": {"range": [0, 25], "tickwidth": 1, "tickcolor": font_color, "nticks": 6},
                "bar": {"color": "#FF9933", "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 1,
                "bordercolor": "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.1)",
                "steps": [
                    {"range": [0, 6], "color": "rgba(19, 136, 8, 0.25)"},      # Low (Proportional)
                    {"range": [6, 13], "color": "rgba(245, 158, 11, 0.25)"},   # Moderate
                    {"range": [13, 25], "color": "rgba(239, 68, 68, 0.25)"},   # High (Disproportionate)
                ],
                "threshold": {
                    "line": {"color": "#E53935", "width": 3},
                    "thickness": 0.75,
                    "value": current_val,
                },
            },
        )
    )
    fig.update_layout(
        margin=dict(l=25, r=25, t=55, b=25),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── 4. Lok Sabha Semicircle Hemicycle Parliament Chart ──
def build_hemicycle_chart(alliance_df: pd.DataFrame, year: int, theme_mode: str = "dark") -> go.Figure:
    """Builds a parliament-style semicircle (hemicycle) chart representing alliance seat strength."""
    is_dark = theme_mode.lower() == "dark"
    font_color = "#F0F6FC" if is_dark else "#0F172A"

    df = alliance_df.copy()
    labels = list(df["alliance"])
    values = list(df["seats"])
    colors = [get_alliance_color(a) for a in labels]

    total_seats = sum(values)
    # Append transparent dummy slice of equal total value to form a top semi-circle
    labels.append("Hidden")
    values.append(total_seats)
    colors.append("rgba(0, 0, 0, 0)")

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                rotation=270,           # Start at 9 o'clock clockwise to 3 o'clock
                direction="clockwise",
                sort=False,
                marker=dict(colors=colors, line=dict(color="#161B22" if is_dark else "#FFFFFF", width=2)),
                textinfo="label+value",
                textposition="inside",
                insidetextorientation="horizontal",
                hoverinfo="label+value+percent",
                showlegend=False,
            )
        ]
    )

    majority_needed = 272
    fig.update_layout(
        title=dict(
            text=f"Lok Sabha Parliament Hemicycle ({year})",
            font=dict(size=16, color=font_color),
            x=0.02,
        ),
        annotations=[
            dict(
                text=f"<b>Total: {total_seats}</b><br><span style='font-size:11px;color:#94A3B8;'>Majority: {majority_needed}</span>",
                x=0.5,
                y=0.25,
                font=dict(size=17, color=font_color, family="Inter"),
                showarrow=False,
            )
        ],
        margin=dict(l=20, r=20, t=50, b=0),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── 5. Sankey Diagram: Parties -> Alliances -> Seats ──
def build_sankey_diagram(clean_df: pd.DataFrame, year: int, theme_mode: str = "dark") -> go.Figure:
    """Creates an interactive Sankey flow from top political parties to coalitions and parliamentary seats."""
    import elections as e

    is_dark = theme_mode.lower() == "dark"
    font_color = "#F0F6FC" if is_dark else "#0F172A"

    yr_df = clean_df[clean_df["year"] == year]
    winners = yr_df[yr_df["position"] == 1]
    party_seats = winners.groupby("party").size().sort_values(ascending=False)

    alliance_map = e.get_alliance_map(year)

    # Focus on parties with >= 1 seat, group small 1-seat into 'Other Parties' if too many
    top_parties = party_seats[party_seats >= 2].to_dict()
    minor_parties_seats = party_seats[party_seats < 2].sum()
    if minor_parties_seats > 0:
        top_parties["Small Parties (<2 seats)"] = minor_parties_seats

    party_names = list(top_parties.keys())
    alliances = ["NDA", "INDIA" if year == 2024 else "UPA", "Others"]

    node_labels = party_names + alliances
    node_indices = {name: i for i, name in enumerate(node_labels)}

    sources = []
    targets = []
    values = []
    link_colors = []

    for party, seats in top_parties.items():
        all_name = alliance_map.get(party, "Others")
        if all_name not in alliances:
            all_name = "Others"
        sources.append(node_indices[party])
        targets.append(node_indices[all_name])
        values.append(int(seats))
        # Color match alliance
        base_color = get_alliance_color(all_name)
        link_colors.append(base_color.replace("#", "rgba(") + ", 0.45)")

    node_colors = [get_party_color(p) for p in party_names] + [get_alliance_color(a) for a in alliances]

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=16,
                    thickness=20,
                    line=dict(color="rgba(255,255,255,0.2)" if is_dark else "rgba(0,0,0,0.2)", width=1),
                    label=node_labels,
                    color=node_colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=["rgba(255,153,51,0.35)" for _ in values],
                ),
            )
        ]
    )

    fig.update_layout(
        title=dict(text=f"Party to Coalition Seat Allocation Flow ({year})", font=dict(color=font_color, size=15)),
        font=dict(family="Inter", size=11, color=font_color),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── 6. Vote vs Seat Proportionality Scatter ──
def build_proportionality_scatter(
    summary_df: pd.DataFrame,
    year: int,
    parties: list[str] | None = None,
    theme_mode: str = "dark",
) -> go.Figure:
    """Builds a scatter bubble chart of popular vote share vs seat share with parity line."""
    is_dark = theme_mode.lower() == "dark"
    font_color = "#F0F6FC" if is_dark else "#0F172A"

    df = summary_df[(summary_df["year"] == year) & (summary_df["votes"] > 0)].copy()
    if parties:
        filtered = df[df["party"].isin(parties)].copy()
        if not filtered.empty:
            df = filtered

    df["Party Color"] = df["party"].map(get_party_color)
    df["display_size"] = df["seats"].clip(lower=1)

    max_share = max(df["vote_share"].max() if not df.empty else 40.0, df["seat_share"].max() if not df.empty else 40.0, 30.0) + 5.0

    fig = px.scatter(
        df,
        x="vote_share",
        y="seat_share",
        size="display_size",
        color="party",
        color_discrete_map={p: get_party_color(p) for p in df["party"].unique()},
        hover_name="party",
        hover_data={
            "vote_share": ":.2f%",
            "seat_share": ":.2f%",
            "seats": True,
            "display_size": False,
            "seat_vote_ratio": ":.2f",
            "party": False,
        },
        text="party",
        labels={"vote_share": "National Vote Share (%)", "seat_share": "Seat Share (%)"},
        title=f"Electoral Parity Landscape ({year}): Popular Vote Share vs Parliamentary Seats",
    )

    # Reference parity line (x = y)
    fig.add_shape(
        type="line",
        line=dict(dash="dash", color="#64748B", width=1.5),
        x0=0,
        x1=max_share,
        y0=0,
        y1=max_share,
    )

    fig.add_annotation(
        x=max_share * 0.75,
        y=max_share * 0.75,
        text="Proportional Parity (1.0)",
        showarrow=False,
        font=dict(color="#64748B", size=11),
        yshift=14,
    )

    fig.update_traces(textposition="top center")
    fig = apply_chart_theme(fig, theme_mode=theme_mode, height=480)
    fig.update_layout(showlegend=False)
    return fig


# ── 7. Animated Bar Chart (Vote vs Seat Multi-Year) ──
def build_animated_vote_seat_bars(summary_df: pd.DataFrame, chosen_parties: list[str], theme_mode: str = "dark") -> go.Figure:
    """Creates a multi-year animated grouped bar chart comparing vote share and seat share across elections."""
    filtered = summary_df[summary_df["party"].isin(chosen_parties)].copy()
    long_df = filtered.melt(
        id_vars=["year", "party"],
        value_vars=["vote_share", "seat_share"],
        var_name="Metric",
        value_name="Percentage",
    )
    long_df["Metric"] = long_df["Metric"].map({"vote_share": "Vote Share (%)", "seat_share": "Seat Share (%)"})

    max_val = max(long_df["Percentage"].max() + 5.0, 50.0)

    fig = px.bar(
        long_df,
        x="party",
        y="Percentage",
        color="Metric",
        barmode="group",
        animation_frame="year",
        range_y=[0, max_val],
        text_auto=".1f",
        title="Longitudinal Progression: Popular Vote Share vs Seat Share (2009–2024)",
        color_discrete_map={"Vote Share (%)": "#00A3E0", "Seat Share (%)": "#FF9933"},
        labels={"party": "Political Party", "Percentage": "Share (%)"},
    )
    fig = apply_chart_theme(fig, theme_mode=theme_mode, height=480)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


# ── 8. Candidate Vote Share Donut ──
def build_constituency_donut(cons_df: pd.DataFrame, theme_mode: str = "dark") -> go.Figure:
    """Builds a modern donut chart of candidate vote distribution in a constituency."""
    is_dark = theme_mode.lower() == "dark"
    font_color = "#F0F6FC" if is_dark else "#0F172A"

    df = cons_df.head(6).copy()
    other_votes = cons_df["votes"].iloc[6:].sum()
    if other_votes > 0:
        other_row = pd.DataFrame([{
            "candidate": "Other Contenders",
            "party": "Others",
            "votes": other_votes,
        }])
        df = pd.concat([df, other_row], ignore_index=True)

    colors = [get_party_color(p) for p in df["party"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=df["candidate"] + " (" + df["party"] + ")",
                values=df["votes"],
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#161B22" if is_dark else "#FFFFFF", width=1.5)),
                textinfo="percent",
                hoverinfo="label+value+percent",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Candidate Vote Share Distribution", font=dict(color=font_color, size=14)),
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color=font_color, size=10), orientation="v"),
    )
    return fig
