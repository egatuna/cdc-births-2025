"""
CDC Provisional Natality 2025 — Interactive Birth-Count Dashboard
==================================================================
A Streamlit dashboard for exploring geographic, monthly, and sex-based
differences in U.S. birth COUNTS (not rates) from CDC WONDER provisional data.

Run locally:   streamlit run app.py
Dependencies:  see requirements.txt (streamlit, pandas, plotly, openpyxl)
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Path relative to this file, so it works locally AND on Streamlit Community Cloud.
DATA_PATH = Path(__file__).parent / "data" / "Provisional_Natality_2025_CDC.xlsx"

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
SEX_OPTIONS = ["Both", "Female", "Male"]

# Colorblind-safe (Okabe-Ito) colors
PRIMARY = "#0072B2"
SEX_COLORS = {"Female": "#E69F00", "Male": "#0072B2"}

# Expected values from the dataset audit — used for validation checks
EXPECTED = {"rows": 1224, "geographies": 51, "months": 12, "sexes": 2, "total": 3_604_640}

# Full name -> USPS abbreviation (50 states + DC). Needed by the Plotly map.
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


# ---------------------------------------------------------------------------
# Data loading & validation
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading CDC workbook…")
def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read the workbook (read-only), rename columns, and enforce month order."""
    raw = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    df = raw.rename(columns={
        "State of Residence": "State",
        "Month Code": "MonthCode",
        "Year Code": "Year",
        "Sex of Infant": "Sex",
    })
    df["State"] = df["State"].str.strip()
    df["Month"] = pd.Categorical(df["Month"].str.strip(), categories=MONTH_ORDER, ordered=True)
    df["Abbr"] = df["State"].map(STATE_ABBR)
    return df.sort_values(["State", "MonthCode", "Sex"]).reset_index(drop=True)


def validate_data(df: pd.DataFrame) -> list[dict]:
    """Return a list of data-quality checks with pass/fail status."""
    month_code_ok = (
        df.groupby("Month", observed=True)["MonthCode"].nunique().eq(1).all()
        and df["Month"].cat.codes.add(1).eq(df["MonthCode"]).all()
    )
    checks = [
        ("Row count", len(df), EXPECTED["rows"]),
        ("Geographies", df["State"].nunique(), EXPECTED["geographies"]),
        ("Months", df["Month"].nunique(), EXPECTED["months"]),
        ("Infant-sex categories", df["Sex"].nunique(), EXPECTED["sexes"]),
        ("Total births", int(df["Births"].sum()), EXPECTED["total"]),
        ("Missing values", int(df.isna().sum().sum()), 0),
        ("Duplicate rows", int(df.duplicated().sum()), 0),
        ("States without map abbreviation", int(df["Abbr"].isna().sum()), 0),
        ("Negative birth counts", int((df["Births"] < 0).sum()), 0),
        ("Month name ↔ code consistent", bool(month_code_ok), True),
    ]
    return [
        {"Check": name, "Observed": obs, "Expected": exp, "Status": "✅ Pass" if obs == exp else "❌ Fail"}
        for name, obs, exp in checks
    ]


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
def reset_filters(all_states: list[str]) -> None:
    """Callback: restore every filter to its default (everything selected)."""
    st.session_state["all_states"] = True
    st.session_state["states"] = all_states
    st.session_state["all_months"] = True
    st.session_state["months"] = MONTH_ORDER
    st.session_state["sex"] = "Both"
    st.session_state["search"] = ""


def _clear_if_unchecked(flag: str, list_key: str) -> None:
    """When a 'Select all' box is unchecked, start the multiselect empty so users pick explicitly."""
    if not st.session_state[flag]:
        st.session_state[list_key] = []


def sidebar_filters(df: pd.DataFrame) -> dict:
    """Render sidebar widgets and return the user's selections."""
    all_states = sorted(df["State"].unique())
    st.session_state.setdefault("states", all_states)
    st.session_state.setdefault("months", MONTH_ORDER)
    st.session_state.setdefault("all_states", True)
    st.session_state.setdefault("all_months", True)
    st.session_state.setdefault("sex", "Both")

    st.sidebar.header("Filters")

    st.sidebar.checkbox("Select all geographies", key="all_states",
                        on_change=_clear_if_unchecked, args=("all_states", "states"))
    if st.session_state["all_states"]:
        states = all_states  # multiselect hidden to avoid 51 chips of clutter
    else:
        states = st.sidebar.multiselect("State / geography", all_states, key="states",
                                        placeholder="Choose one or more states")

    st.sidebar.checkbox("Select all months", key="all_months",
                        on_change=_clear_if_unchecked, args=("all_months", "months"))
    if st.session_state["all_months"]:
        months = MONTH_ORDER
    else:
        months = st.sidebar.multiselect("Month", MONTH_ORDER, key="months",
                                        placeholder="Choose one or more months")
    months = [m for m in MONTH_ORDER if m in months]  # keep calendar order

    sex = st.sidebar.radio("Sex of infant", SEX_OPTIONS, key="sex", horizontal=True)

    st.sidebar.button("↺ Reset filters", on_click=reset_filters, args=(all_states,), width="stretch")

    # Active filter summary
    st.sidebar.divider()
    st.sidebar.subheader("Active filters")
    geo_txt = "All 51 geographies" if len(states) == len(all_states) else (
        f"{len(states)} selected" + (f": {', '.join(states)}" if 0 < len(states) <= 5 else ""))
    month_txt = "All 12 months" if len(months) == 12 else (
        f"{len(months)} selected" + (f": {', '.join(m[:3] for m in months)}" if months else ""))
    st.sidebar.markdown(f"- **Geography:** {geo_txt}\n- **Months:** {month_txt}\n- **Sex:** {sex}")

    return {"states": states, "months": months, "sex": sex}


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Filter the data frame by the selected states, months, and sex."""
    mask = df["State"].isin(f["states"]) & df["Month"].isin(f["months"])
    if f["sex"] != "Both":
        mask &= df["Sex"].eq(f["sex"])
    return df.loc[mask]


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
def show_kpis(fdf: pd.DataFrame, f: dict) -> None:
    total = int(fdf["Births"].sum())
    by_state = fdf.groupby("State")["Births"].sum()
    by_month = fdf.groupby("Month", observed=True)["Births"].sum()
    n_months = len(f["months"])

    # Two rows (3 + 2) so long values like "California" never truncate on laptop-width screens
    row1, row2 = st.columns(3), st.columns(2)
    c = [*row1, *row2]
    c[0].metric("Total births", f"{total:,}", border=True)
    c[1].metric("Geographies selected", f"{len(f['states']):,}", border=True)
    c[2].metric("Avg births per month", f"{total / n_months:,.0f}", border=True,
                help="Total births in the selection ÷ number of selected months.")
    c[3].metric("Top geography", by_state.idxmax(), border=True,
                help=f"{by_state.idxmax()}: {by_state.max():,} births in the current selection.")
    c[3].caption(f"{by_state.max():,} births")
    c[4].metric("Top month", str(by_month.idxmax()), border=True,
                help=f"{by_month.idxmax()}: {by_month.max():,} births in the current selection.")
    c[4].caption(f"{by_month.max():,} births")


# ---------------------------------------------------------------------------
# Chart builders (each returns a Plotly figure)
# ---------------------------------------------------------------------------
def _short_months(fig: go.Figure) -> go.Figure:
    """Show 3-letter month ticks (full names stay in tooltips) so labels don't rotate."""
    fig.update_xaxes(tickvals=MONTH_ORDER, ticktext=[m[:3] for m in MONTH_ORDER], title="Month")
    return fig


def _style(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=60, b=10),
                      separators=".,", hoverlabel=dict(font_size=13))
    return fig


def chart_monthly_trend(fdf: pd.DataFrame) -> go.Figure:
    m = fdf.groupby("Month", observed=True)["Births"].sum().reset_index()
    fig = px.line(m, x="Month", y="Births", markers=True,
                  title="Monthly births (selected geographies & sex)",
                  category_orders={"Month": MONTH_ORDER}, color_discrete_sequence=[PRIMARY])
    fig.update_traces(hovertemplate="%{x}: %{y:,} births<extra></extra>")
    fig.update_yaxes(rangemode="tozero", tickformat=",", title="Births (count)")
    return _style(_short_months(fig))


def chart_sex_by_month(fdf: pd.DataFrame) -> go.Figure:
    m = fdf.groupby(["Month", "Sex"], observed=True)["Births"].sum().reset_index()
    fig = px.bar(m, x="Month", y="Births", color="Sex", barmode="group",
                 title="Female vs. male births by month",
                 category_orders={"Month": MONTH_ORDER, "Sex": ["Female", "Male"]},
                 color_discrete_map=SEX_COLORS)
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:,}<extra></extra>")
    fig.update_yaxes(rangemode="tozero", tickformat=",", title="Births (count)")
    return _style(_short_months(fig))


def chart_sex_totals(fdf: pd.DataFrame) -> go.Figure:
    s = fdf.groupby("Sex")["Births"].sum().reindex(["Female", "Male"]).dropna().reset_index()
    fig = px.bar(s, x="Sex", y="Births", color="Sex", text="Births",
                 title="Total births by sex", color_discrete_map=SEX_COLORS)
    fig.update_traces(texttemplate="%{y:,}", textposition="outside",
                      hovertemplate="%{x}: %{y:,} births<extra></extra>", cliponaxis=False)
    fig.update_yaxes(rangemode="tozero", tickformat=",", title="Births (count)")
    fig.update_layout(showlegend=False)
    return _style(fig)


def chart_state_ranking(fdf: pd.DataFrame) -> go.Figure:
    s = fdf.groupby("State")["Births"].sum().sort_values().reset_index()
    fig = px.bar(s, x="Births", y="State", orientation="h",
                 title="Geographies ranked by births", color_discrete_sequence=[PRIMARY])
    fig.update_traces(hovertemplate="%{y}: %{x:,} births<extra></extra>")
    fig.update_xaxes(rangemode="tozero", tickformat=",", title="Births (count)")
    fig.update_yaxes(title=None)
    return _style(fig, height=max(320, 18 * len(s) + 100))


def chart_map(fdf: pd.DataFrame) -> go.Figure:
    s = fdf.groupby(["State", "Abbr"])["Births"].sum().reset_index()
    fig = px.choropleth(s, locations="Abbr", locationmode="USA-states", color="Births",
                        scope="usa", hover_name="State", color_continuous_scale="Blues",
                        title="Births by state of residence")
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>%{z:,} births<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(title="Births", tickformat=","))
    return _style(fig, height=480)


def chart_heatmap(fdf: pd.DataFrame) -> go.Figure:
    p = (fdf.pivot_table(index="State", columns="Month", values="Births",
                         aggfunc="sum", observed=True)
         .reindex(columns=[m for m in MONTH_ORDER if m in fdf["Month"].unique()]))
    p = p.loc[p.sum(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(p, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(x="Month", y="State", color="Births"),
                    title="State × month heatmap (sorted by total births)")
    fig.update_traces(hovertemplate="%{y}, %{x}: %{z:,} births<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(tickformat=","))
    return _style(fig, height=max(320, 16 * len(p) + 140))


def chart_top_bottom(fdf: pd.DataFrame, n: int = 5) -> go.Figure:
    s = fdf.groupby("State")["Births"].sum().sort_values(ascending=False)
    n = min(n, len(s) // 2) if len(s) > 1 else 1
    top, bottom = s.head(n), s.tail(n) if len(s) > 1 else s.iloc[0:0]
    d = pd.concat([top.rename("Births").to_frame().assign(Group=f"Top {n}"),
                   bottom.rename("Births").to_frame().assign(Group=f"Bottom {n}")]).reset_index()
    fig = px.bar(d, x="Births", y="State", color="Group", orientation="h", text="Births",
                 title=f"Top {n} vs. bottom {n} geographies",
                 color_discrete_map={f"Top {n}": PRIMARY, f"Bottom {n}": "#D55E00"})
    fig.update_traces(texttemplate="%{x:,}", textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}: %{x:,} births<extra></extra>")
    fig.update_xaxes(range=[0, d["Births"].max() * 1.22], tickformat=",", title="Births (count)")
    fig.update_yaxes(title=None, categoryorder="total ascending")
    fig.update_layout(legend=dict(orientation="h", y=-0.18, x=0, title=None))
    return _style(fig, height=max(300, 40 * len(d) + 120))


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------
def show_header() -> None:
    st.title("U.S. Births 2025 — CDC Provisional Natality Dashboard")
    st.markdown(
        "Explore how **birth counts** differ across states, months, and infant sex in 2025. "
        "Source: [CDC WONDER — Provisional Natality Data](https://wonder.cdc.gov/natality-provisional-current.html), "
        "National Center for Health Statistics."
    )
    st.warning(
        "**Provisional data.** These 2025 figures are preliminary and may be revised by CDC. "
        "All values are **birth counts, not birth rates** — larger states have more births "
        "largely because they have more people.",
        icon="⚠️",
    )


def tab_data_table(fdf: pd.DataFrame) -> None:
    st.subheader("Filtered data")
    query = st.text_input("Search table (any column)", key="search",
                          placeholder="e.g. Texas, March, Female")
    table = fdf[["State", "Abbr", "Month", "MonthCode", "Year", "Sex", "Births"]].copy()
    table["Month"] = table["Month"].astype(str)
    if query:
        hit = table.astype(str).apply(lambda col: col.str.contains(query, case=False, regex=False))
        table = table[hit.any(axis=1)]
    st.caption(f"{len(table):,} rows · {int(table['Births'].sum()):,} births shown")
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Births": st.column_config.NumberColumn(format="localized"),
                                "Year": st.column_config.NumberColumn(format="plain"),
                                "MonthCode": st.column_config.NumberColumn("Month code")})
    st.download_button("⬇ Download filtered data (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name="cdc_births_2025_filtered.csv", mime="text/csv",
                       disabled=table.empty)


def tab_about(df: pd.DataFrame) -> None:
    st.subheader("About the data")
    st.markdown(
        """
- **Source:** CDC WONDER, Provisional Natality, National Center for Health Statistics.
- **Coverage:** Calendar year 2025 · 50 states + District of Columbia · 12 months · Female/Male.
- **Unit:** Each row is the **number of live births** for one state, month, and infant sex (1,224 rows).
- **Provisional:** Figures are preliminary and can change when CDC finalizes the data.
- **What this dashboard does *not* show:** birth rates, fertility rates, or percentages of population.
  The file contains no population denominators, so any rate would be invented.
- **Interpretation tip:** Compare states with care — California has more births than Wyoming mainly
  because it has far more residents, not because births are "more likely" there.
- **Month order:** Months are sorted by the CDC *Month Code* (1–12), not alphabetically.
        """
    )
    st.subheader("Data-validation checks")
    st.dataframe(pd.DataFrame(validate_data(df)).astype(str), hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="CDC Births 2025 Dashboard", page_icon="📊", layout="wide")

    try:
        df = load_data()
    except FileNotFoundError:
        st.error(f"Data file not found at `{DATA_PATH}`. Place the workbook inside the `data/` folder.")
        st.stop()

    show_header()

    failed = [c for c in validate_data(df) if c["Status"].startswith("❌")]
    if failed:
        st.error("Data-validation issue(s): " + "; ".join(f"{c['Check']} = {c['Observed']}" for c in failed))

    filters = sidebar_filters(df)
    fdf = apply_filters(df, filters)

    if not filters["states"] or not filters["months"] or fdf.empty:
        st.info("**No observations match the current filters.** Select at least one geography and "
                "one month, or click **↺ Reset filters** in the sidebar.", icon="ℹ️")
        st.stop()

    show_kpis(fdf, filters)

    t1, t2, t3, t4, t5 = st.tabs(["Overview", "Geographic Analysis", "Monthly & Sex Analysis",
                                  "Data Table & Download", "About the Data"])
    with t1:
        left, right = st.columns([3, 2])
        left.plotly_chart(chart_monthly_trend(fdf), width="stretch")
        right.plotly_chart(chart_sex_totals(fdf), width="stretch")
        st.plotly_chart(chart_map(fdf), width="stretch")
    with t2:
        st.plotly_chart(chart_map(fdf), width="stretch", key="map_geo")
        left, right = st.columns(2)
        left.plotly_chart(chart_state_ranking(fdf), width="stretch")
        right.plotly_chart(chart_top_bottom(fdf), width="stretch")
        st.plotly_chart(chart_heatmap(fdf), width="stretch")
    with t3:
        st.plotly_chart(chart_monthly_trend(fdf), width="stretch", key="trend_t3")
        st.plotly_chart(chart_sex_by_month(fdf), width="stretch")
        st.caption("Bars start at zero so differences between female and male counts are not exaggerated.")
    with t4:
        tab_data_table(fdf)
    with t5:
        tab_about(df)

    st.caption("Built with Streamlit, pandas, and Plotly · Data: CDC WONDER Provisional Natality (2025).")


if __name__ == "__main__":
    main()
