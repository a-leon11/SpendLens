import pandas as pd
import pytest

from spendlens import budget, charts, portfolio, sample_data


def _rows(spec: dict) -> list[dict]:
    """The single inline dataset of a Vega-Lite spec."""
    (rows,) = spec["datasets"].values()
    return rows


@pytest.fixture(scope="module")
def sample():
    income, expenses, investments = sample_data.generate(months=6)
    return income, expenses, investments


def test_monthly_chart_has_one_bar_per_month_and_series(sample):
    income, expenses, _ = sample
    monthly = budget.monthly_summary(income, expenses)

    spec = charts.monthly_chart(monthly).to_dict()
    rows = _rows(spec)

    assert len(rows) == len(monthly) * 2
    assert sorted({r["month"] for r in rows}) == [str(p) for p in monthly.index]
    # A month axis, not a continuous time axis: that drew each bar one day wide.
    assert spec["encoding"]["x"]["type"] == "ordinal"
    # Grouped, not stacked on top of each other.
    assert "xOffset" in spec["encoding"]


def test_category_chart_has_one_bar_per_category_largest_first(sample):
    _, expenses, _ = sample
    totals = budget.category_breakdown(expenses)

    spec = charts.category_chart(totals).to_dict()

    assert len(_rows(spec)) == len(totals)
    assert spec["encoding"]["y"]["sort"] == "-x"


def test_allocation_chart_shares_sum_to_one(sample):
    _, _, investments = sample
    positions = portfolio.build_positions(investments, prices={})

    spec = charts.allocation_chart(positions).to_dict()
    rows = _rows(spec)

    assert len(rows) == len(positions)
    assert sum(r["share"] for r in rows) == pytest.approx(1.0)
