import pandas as pd

from spendlens import budget


def _expenses(rows):
    frame = pd.DataFrame(rows, columns=["date", "description", "amount", "category"])
    return frame.assign(date=pd.to_datetime(frame["date"]))


def test_budget_follows_its_effective_date():
    expenses = _expenses([
        ("2025-01-05", "Rent", 1000.0, "Housing"),
        ("2025-02-05", "Rent", 1000.0, "Housing"),
        ("2025-03-05", "Rent", 1200.0, "Housing"),
    ])
    budgets = pd.DataFrame({
        "category": ["Housing", "Housing"],
        "monthly_budget": [1000.0, 1200.0],
        "effective_from": pd.to_datetime(["2025-01-01", "2025-03-01"]),
    })

    bva = budget.budget_vs_actual(expenses, budgets)

    assert list(bva["budget"]) == [1000.0, 1000.0, 1200.0]
    assert (bva["variance"] == 0).all()
    assert set(bva["status"]) == {"within"}


def test_over_within_and_unbudgeted_statuses():
    expenses = _expenses([
        ("2025-01-10", "Lunch", 150.0, "Food"),
        ("2025-02-10", "Flights", 300.0, "Travel"),
    ])
    budgets = pd.DataFrame({
        "category": ["Food"],
        "monthly_budget": [100.0],
        "effective_from": pd.to_datetime(["2025-01-01"]),
    })

    bva = budget.budget_vs_actual(expenses, budgets).set_index(["month", "category"])
    jan, feb = pd.Period("2025-01"), pd.Period("2025-02")

    assert bva.loc[(jan, "Food"), "status"] == "over"
    assert bva.loc[(jan, "Food"), "variance"] == 50.0
    assert bva.loc[(jan, "Food"), "variance_pct"] == 0.5
    # A month with no spending is still compared with its budget.
    assert bva.loc[(feb, "Food"), "actual"] == 0.0
    assert bva.loc[(feb, "Food"), "status"] == "within"
    # Spending with no budget is reported, not dropped.
    assert bva.loc[(feb, "Travel"), "status"] == "unbudgeted"
    # No budget and no spending: no row at all.
    assert (jan, "Travel") not in bva.index


def test_rolling_variance_smooths_a_lumpy_bill():
    # A 300 quarterly bill against a 100 monthly budget: wild month to month,
    # exactly on budget over any 3-month window.
    expenses = _expenses([
        ("2025-01-05", "Premium", 300.0, "Insurance"),
        ("2025-04-05", "Premium", 300.0, "Insurance"),
        ("2025-06-28", "Filler", 1.0, "Other"),
    ])
    budgets = pd.DataFrame({
        "category": ["Insurance"],
        "monthly_budget": [100.0],
        "effective_from": pd.to_datetime(["2025-01-01"]),
    })
    bva = budget.budget_vs_actual(expenses, budgets)
    insurance = bva[bva["category"] == "Insurance"]
    assert insurance["variance_pct"].max() == 2.0 and insurance["variance_pct"].min() == -1.0

    rolled = budget.rolling_variance(bva, window=3)
    rolled = rolled[rolled["category"] == "Insurance"]

    assert len(rolled) == 4                  # Jan-Jun, needs 3 months of history: Mar to Jun
    assert (rolled["variance"] == 0).all()   # every 3-month window holds exactly one premium
    assert (rolled["budget"] == 300.0).all()


def test_rolling_variance_leaves_out_categories_without_a_budget():
    expenses = _expenses([
        ("2025-01-10", "Flights", 300.0, "Travel"),
        ("2025-02-10", "Flights", 300.0, "Travel"),
        ("2025-03-10", "Flights", 300.0, "Travel"),
    ])
    budgets = pd.DataFrame({
        "category": ["Food"], "monthly_budget": [100.0], "effective_from": pd.to_datetime(["2025-01-01"]),
    })

    rolled = budget.rolling_variance(budget.budget_vs_actual(expenses, budgets), window=3)

    assert "Travel" not in set(rolled["category"])


def test_summary_totals_per_category_and_sorts_unbudgeted_last():
    expenses = _expenses([
        ("2025-01-10", "Lunch", 150.0, "Food"),
        ("2025-02-10", "Flights", 300.0, "Travel"),
    ])
    budgets = pd.DataFrame({
        "category": ["Food"],
        "monthly_budget": [100.0],
        "effective_from": pd.to_datetime(["2025-01-01"]),
    })

    summary = budget.budget_summary(budget.budget_vs_actual(expenses, budgets))
    by_category = summary.set_index("category")

    assert list(summary["category"]) == ["Food", "Travel"]
    assert by_category.loc["Food", "budget"] == 200.0
    assert by_category.loc["Food", "actual"] == 150.0
    assert by_category.loc["Food", "variance"] == -50.0
    assert pd.isna(by_category.loc["Travel", "budget"])
