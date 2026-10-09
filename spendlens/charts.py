"""Altair charts for the dashboard. Pure functions: DataFrame in, chart out.

Built explicitly instead of with st.bar_chart because a datetime index puts
the axis on a continuous time scale, which draws each monthly bar one day
wide, and multiple series are stacked by default (income stacked on expenses).
"""
from __future__ import annotations

import altair as alt
import pandas as pd

INCOME_COLOR = "#2a9d8f"
EXPENSE_COLOR = "#e76f51"
BAR_COLOR = "#4c78a8"
ROW_HEIGHT = 26


def monthly_chart(monthly: pd.DataFrame) -> alt.Chart:
    """Grouped bars, one pair (income, expenses) per month on a month axis."""
    frame = monthly[["income", "expenses"]].copy()
    frame.index = frame.index.astype(str)  # "2024-10": categorical, sorts chronologically
    frame.index.name = "month"
    long = frame.reset_index().melt(id_vars="month", var_name="series", value_name="amount")

    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=-45)),
            xOffset=alt.XOffset("series:N"),
            y=alt.Y("amount:Q", title="MXN", axis=alt.Axis(format=",.0f")),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(domain=["income", "expenses"], range=[INCOME_COLOR, EXPENSE_COLOR]),
            ),
            tooltip=[
                alt.Tooltip("month:O", title="Month"),
                alt.Tooltip("series:N", title="Type"),
                alt.Tooltip("amount:Q", title="MXN", format=",.2f"),
            ],
        )
        .properties(height=320, width="container")
    )


def savings_rate_chart(monthly: pd.DataFrame) -> alt.LayerChart:
    """Monthly savings rate and its 3-month average (net saved / income)."""
    frame = monthly[["income", "net", "savings_rate"]].copy()
    frame["3-month average"] = frame["net"].rolling(3).sum() / frame["income"].rolling(3).sum()
    frame = frame.rename(columns={"savings_rate": "monthly"})
    frame.index = frame.index.astype(str)
    frame.index.name = "month"
    long = frame[["monthly", "3-month average"]].reset_index().melt(
        id_vars="month", var_name="series", value_name="rate"
    )

    lines = (
        alt.Chart(long)
        .mark_line(point=alt.OverlayMarkDef(size=30))
        .encode(
            x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("rate:Q", title="Savings rate", axis=alt.Axis(format=".0%")),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(domain=["monthly", "3-month average"], range=["#9aa5b1", "#4c78a8"]),
            ),
            tooltip=[
                alt.Tooltip("month:O", title="Month"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("rate:Q", title="Savings rate", format=".1%"),
            ],
        )
    )
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#999", strokeDash=[4, 4]).encode(y="y:Q")
    return (lines + zero).properties(height=260, width="container")


def budget_heatmap(bva: pd.DataFrame, window: int = 1) -> alt.Chart:
    """Month by category grid coloured by variance vs budget: red over, blue under.

    `window` is only used to label the tooltip when the input is a rolling total.
    """
    span = "" if window == 1 else f" ({window} mo)"
    data = bva.dropna(subset=["variance_pct"]).copy()
    data["month"] = data["month"].astype(str)
    return (
        alt.Chart(data)
        .mark_rect()
        .encode(
            x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("category:N", title=None),
            color=alt.Color(
                "variance_pct:Q",
                title="vs budget",
                scale=alt.Scale(scheme="redblue", domain=[-0.5, 0.5], reverse=True, clamp=True),
                legend=alt.Legend(format="+.0%"),
            ),
            tooltip=[
                alt.Tooltip("month:O", title="Month"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("actual:Q", title=f"Actual{span}", format=",.0f"),
                alt.Tooltip("budget:Q", title=f"Budget{span}", format=",.0f"),
                alt.Tooltip("variance:Q", title=f"Variance{span}", format="+,.0f"),
                alt.Tooltip("variance_pct:Q", title="Variance %", format="+.0%"),
            ],
        )
        .properties(height=alt.Step(24), width="container")
    )


def recurring_spend_chart(spend: pd.DataFrame) -> alt.Chart:
    """Stacked monthly spend on recurring charges, by category."""
    data = spend.copy()
    data["month"] = data["month"].astype(str)
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("amount:Q", title="MXN", axis=alt.Axis(format=",.0f")),
            color=alt.Color("category:N", title=None),
            tooltip=[
                alt.Tooltip("month:O", title="Month"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("amount:Q", title="MXN", format=",.2f"),
            ],
        )
        .properties(height=280, width="container")
    )


def category_chart(totals: pd.Series) -> alt.Chart:
    """Horizontal bars of total spend per category, largest on top."""
    data = totals.rename("amount").rename_axis("category").reset_index()
    return (
        alt.Chart(data)
        .mark_bar(color=BAR_COLOR)
        .encode(
            y=alt.Y("category:N", sort="-x", title=None),
            x=alt.X("amount:Q", title="MXN", axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("amount:Q", title="MXN", format=",.2f"),
            ],
        )
        .properties(height=alt.Step(ROW_HEIGHT), width="container")
    )


def allocation_chart(positions: pd.DataFrame) -> alt.LayerChart:
    """Horizontal bars of portfolio value per ticker with the share labelled."""
    data = positions[["ticker", "value", "price_source"]].copy()
    data["share"] = data["value"] / data["value"].sum()

    y = alt.Y("ticker:N", sort="-x", title=None)
    bars = (
        alt.Chart(data)
        .mark_bar(color=BAR_COLOR)
        .encode(
            y=y,
            x=alt.X("value:Q", title="USD", axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("ticker:N", title="Ticker"),
                alt.Tooltip("value:Q", title="USD", format=",.2f"),
                alt.Tooltip("share:Q", title="Share", format=".1%"),
                alt.Tooltip("price_source:N", title="Price source"),
            ],
        )
    )
    labels = (
        alt.Chart(data)
        .mark_text(align="left", dx=4)
        .encode(y=y, x="value:Q", text=alt.Text("share:Q", format=".1%"))
    )
    return (bars + labels).properties(height=alt.Step(ROW_HEIGHT), width="container")
