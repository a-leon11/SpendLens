import pytest

from spendlens import budget, charts, portfolio, recurring, sample_data


def _rows(spec: dict) -> list[dict]:
    """The single inline dataset of a Vega-Lite spec."""
    (rows,) = spec["datasets"].values()
    return rows


@pytest.fixture(scope="module")
def sample():
    return sample_data.generate(months=6)


def test_monthly_chart_has_one_bar_per_month_and_series(sample):
    monthly = budget.monthly_summary(sample.income, sample.expenses)

    spec = charts.monthly_chart(monthly).to_dict()
    rows = _rows(spec)

    assert len(rows) == len(monthly) * 2
    assert sorted({r["month"] for r in rows}) == [str(p) for p in monthly.index]
    # A month axis, not a continuous time axis: that drew each bar one day wide.
    assert spec["encoding"]["x"]["type"] == "ordinal"
    # Grouped, not stacked on top of each other.
    assert "xOffset" in spec["encoding"]


def test_category_chart_has_one_bar_per_category_largest_first(sample):
    totals = budget.category_breakdown(sample.expenses)

    spec = charts.category_chart(totals).to_dict()

    assert len(_rows(spec)) == len(totals)
    assert spec["encoding"]["y"]["sort"] == "-x"


def test_allocation_chart_shares_sum_to_one(sample):
    positions = portfolio.build_positions(sample.investments, prices={})

    spec = charts.allocation_chart(positions).to_dict()
    rows = _rows(spec)

    assert len(rows) == len(positions)
    assert sum(r["share"] for r in rows) == pytest.approx(1.0)


def test_savings_rate_chart_has_both_series_for_every_month(sample):
    monthly = budget.monthly_summary(sample.income, sample.expenses)

    spec = charts.savings_rate_chart(monthly).to_dict()
    rows = next(iter(spec["datasets"].values()))

    assert {r["series"] for r in rows if "series" in r} == {"monthly", "3-month average"}
    assert len([r for r in rows if "series" in r]) == len(monthly) * 2


def test_budget_heatmap_has_a_cell_for_every_budgeted_month_and_category(sample):
    bva = budget.budget_vs_actual(sample.expenses, sample.budgets)

    spec = charts.budget_heatmap(bva).to_dict()

    assert len(_rows(spec)) == bva["variance_pct"].notna().sum()
    assert spec["encoding"]["color"]["scale"]["scheme"] == "redblue"


def test_recurring_spend_chart_matches_the_input_rows(sample):
    report = recurring.analyze_recurring(sample.expenses)
    spend = recurring.recurring_spend_by_month(sample.expenses, report.items)

    spec = charts.recurring_spend_chart(spend).to_dict()

    assert len(_rows(spec)) == len(spend)
