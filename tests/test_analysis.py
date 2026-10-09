import pandas as pd
import pytest

from spendlens import budget, portfolio


def test_monthly_summary_math():
    income = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-15", "2025-01-31", "2025-02-15"]),
        "amount": [1000.0, 1000.0, 500.0],
    })
    expenses = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-02", "2025-03-05"]),
        "amount": [400.0, 100.0],
    })

    summary = budget.monthly_summary(income, expenses)

    jan = summary.loc[pd.Period("2025-01")]
    assert (jan["income"], jan["expenses"], jan["net"]) == (2000.0, 400.0, 1600.0)
    assert jan["savings_rate"] == pytest.approx(0.8)

    feb = summary.loc[pd.Period("2025-02")]
    assert feb["expenses"] == 0.0 and feb["savings_rate"] == pytest.approx(1.0)

    # expenses with no income: negative net, savings rate undefined (not inf)
    mar = summary.loc[pd.Period("2025-03")]
    assert mar["net"] == -100.0 and pd.isna(mar["savings_rate"])


def test_category_breakdown_is_sorted_largest_first():
    expenses = pd.DataFrame({"category": ["Food", "Rent", "Food"], "amount": [50.0, 500.0, 70.0]})
    result = budget.category_breakdown(expenses)
    assert list(result.index) == ["Rent", "Food"]
    assert result["Food"] == 120.0


LOTS = pd.DataFrame({
    "ticker": ["VOO", "VOO", "MSFT"],
    "shares": [1.0, 2.0, 1.0],
    "buy_price": [100.0, 110.0, 300.0],
    "buy_date": pd.to_datetime(["2025-01-10", "2025-02-10", "2025-01-20"]),
})


def test_positions_aggregate_lots_and_use_live_price():
    positions = portfolio.build_positions(LOTS, {"VOO": 120.0, "MSFT": 330.0})
    voo = positions.set_index("ticker").loc["VOO"]

    assert voo["shares"] == 3.0
    assert voo["cost"] == pytest.approx(320.0)          # 100 + 2 * 110
    assert voo["market_value"] == pytest.approx(360.0)  # 3 * 120
    assert voo["unrealized_gain"] == pytest.approx(40.0)
    assert voo["return_pct"] == pytest.approx(12.5)
    assert voo["price_source"] == "live"


def test_positions_fall_back_to_cost_basis_without_a_price():
    positions = portfolio.build_positions(LOTS, {"VOO": 120.0})
    msft = positions.set_index("ticker").loc["MSFT"]

    assert msft["value"] == pytest.approx(300.0)
    assert msft["price_source"] == "cost basis"
    assert pd.isna(msft["unrealized_gain"])
