import pandas as pd
import pytest

from spendlens import returns


def test_xirr_one_year_matches_the_closed_form():
    # 1000 in, 1100 out exactly 365 days later: 10% a year.
    rate = returns.xirr([(pd.Timestamp("2025-01-01"), -1000.0), (pd.Timestamp("2026-01-01"), 1100.0)])
    assert rate == pytest.approx(0.10, abs=1e-6)


def test_xirr_two_years_is_annualised():
    # 1000 grows to 1210 over 730 days: 10% a year, not 21%.
    rate = returns.xirr([(pd.Timestamp("2024-01-01"), -1000.0), (pd.Timestamp("2025-12-31"), 1210.0)])
    assert rate == pytest.approx(0.10, abs=1e-3)


def test_xirr_solution_zeroes_the_npv():
    flows = [
        (pd.Timestamp("2025-01-01"), -1000.0),
        (pd.Timestamp("2025-07-01"), -500.0),
        (pd.Timestamp("2026-03-01"), 1800.0),
    ]
    rate = returns.xirr(flows)

    start = flows[0][0]
    npv = sum(amount / (1 + rate) ** ((date - start).days / 365.0) for date, amount in flows)
    assert npv == pytest.approx(0.0, abs=1e-6)


def test_xirr_is_negative_for_a_loss():
    rate = returns.xirr([(pd.Timestamp("2025-01-01"), -1000.0), (pd.Timestamp("2026-01-01"), 900.0)])
    assert rate == pytest.approx(-0.10, abs=1e-6)


def test_xirr_returns_none_without_both_money_in_and_out():
    day = pd.Timestamp("2025-01-01")
    assert returns.xirr([(day, -100.0), (day + pd.Timedelta(days=30), -100.0)]) is None
    assert returns.xirr([(day, -100.0)]) is None


def _lots():
    return pd.DataFrame({
        "ticker": ["VOO"],
        "shares": [10.0],
        "buy_price": [100.0],
        "buy_date": pd.to_datetime(["2025-01-01"]),
    })


def test_portfolio_xirr_for_a_single_lot():
    rate = returns.portfolio_xirr(_lots(), {"VOO": 110.0}, as_of="2026-01-01")
    assert rate == pytest.approx(0.10, abs=1e-6)


def test_portfolio_xirr_needs_a_price_for_every_ticker():
    lots = pd.concat([_lots(), _lots().assign(ticker="MSFT")], ignore_index=True)
    assert returns.portfolio_xirr(lots, {"VOO": 110.0}, as_of="2026-01-01") is None
