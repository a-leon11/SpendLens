import pandas as pd
import pytest

from spendlens import recurring, sample_data


def _expenses(rows):
    frame = pd.DataFrame(rows, columns=["date", "description", "amount", "category"])
    return frame.assign(date=pd.to_datetime(frame["date"]))


def _monthly(description, amounts, day=5, start="2024-01", category="Subscriptions"):
    months = pd.period_range(start, periods=len(amounts), freq="M")
    return [
        (pd.Timestamp(year=m.year, month=m.month, day=day), description, amount, category)
        for m, amount in zip(months, amounts)
    ]


def test_detects_price_change_and_duplicate_and_ignores_irregular_spending():
    rows = _monthly("Streamer", [10.0] * 5 + [12.0] * 5)  # price rises in June
    rows.append((pd.Timestamp("2024-03-06"), "Streamer", 10.0, "Subscriptions"))  # charged twice in March
    # groceries on scattered days: frequent, but not a subscription
    for month, day in zip(pd.period_range("2024-01", periods=10, freq="M"), [3, 17, 9, 25, 12, 28, 6, 21, 15, 1]):
        rows.append((pd.Timestamp(year=month.year, month=month.month, day=day), "Soriana", 400.0, "Groceries"))

    report = recurring.analyze_recurring(_expenses(rows))

    assert list(report.items["description"]) == ["Streamer"]
    streamer = report.items.iloc[0]
    assert streamer["cadence"] == "monthly" and streamer["active"]
    assert streamer["latest_amount"] == 12.0 and streamer["annual_cost"] == pytest.approx(144.0)

    assert list(report.price_changes["month"]) == ["2024-06"]
    change = report.price_changes.iloc[0]
    assert (change["old_amount"], change["new_amount"]) == (10.0, 12.0)
    assert change["annual_impact"] == pytest.approx(24.0)

    assert list(report.duplicates["month"]) == ["2024-03"]
    assert report.duplicates.iloc[0]["wasted"] == 10.0


def test_a_charge_that_stopped_is_inactive():
    rows = _monthly("Old plan", [20.0] * 4)  # Jan to Apr, then nothing
    rows.append((pd.Timestamp("2024-12-28"), "Filler", 5.0, "Other"))  # data runs to December

    report = recurring.analyze_recurring(_expenses(rows))

    assert not report.items.set_index("description").loc["Old plan", "active"]


def test_recurring_found_in_sample_data_matches_what_was_planted():
    sample = sample_data.generate()
    report = recurring.analyze_recurring(sample.expenses)
    items = report.items.set_index("description")

    assert items.loc["Insurance premium", "cadence"] == "quarterly"
    assert items.loc["Insurance premium", "monthly_cost"] == pytest.approx(400.0)
    assert items.loc["Domain renewal", "cadence"] == "yearly"
    assert items.loc["Electricity bill", "cadence"] == "every 2 months"
    assert items.loc["Electricity bill", "variable"]

    assert not items.loc["Disney+", "active"]      # cancelled
    assert items.loc["Language app", "active"]     # added later
    assert items.loc["Rent", "active"]

    # Frequent but irregular spending is not recurring, and neither is a seasonal purchase.
    for name in ["Soriana", "HEB", "Ride share", "Transit card top-up", "Pharmacy", "Holiday gifts"]:
        assert name not in items.index

    changes = report.price_changes.set_index(["description", "month"])
    assert changes.loc[("Spotify", "2024-12"), "new_amount"] == 149.0
    assert changes.loc[("Netflix", "2025-12"), "new_amount"] == 249.0
    assert ("Rent", "2024-10") in changes.index and ("Rent", "2025-10") in changes.index
    assert "Electricity bill" not in set(report.price_changes["description"])  # variable: no alerts

    assert list(report.duplicates["description"]) == ["Netflix"]
    assert list(report.duplicates["month"]) == ["2024-05"]


def test_recurring_spend_by_month_only_counts_recurring_items():
    sample = sample_data.generate(months=12)
    report = recurring.analyze_recurring(sample.expenses)

    spend = recurring.recurring_spend_by_month(sample.expenses, report.items)

    expected = sample.expenses[sample.expenses["description"].isin(report.items["description"])]["amount"].sum()
    assert spend["amount"].sum() == pytest.approx(expected)
