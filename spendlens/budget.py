"""Monthly budget summaries from income and expense tables."""
from __future__ import annotations

import numpy as np
import pandas as pd


def monthly_summary(income: pd.DataFrame, expenses: pd.DataFrame) -> pd.DataFrame:
    """One row per month: income, expenses, net, savings_rate (net / income)."""
    monthly_income = income.groupby(income["date"].dt.to_period("M"))["amount"].sum()
    monthly_expenses = expenses.groupby(expenses["date"].dt.to_period("M"))["amount"].sum()

    summary = pd.concat({"income": monthly_income, "expenses": monthly_expenses}, axis=1)
    summary = summary.fillna(0.0).sort_index()
    summary["net"] = summary["income"] - summary["expenses"]
    summary["savings_rate"] = (summary["net"] / summary["income"]).where(summary["income"] > 0)
    return summary


def category_breakdown(expenses: pd.DataFrame) -> pd.Series:
    """Total spend per category, largest first."""
    return expenses.groupby("category")["amount"].sum().sort_values(ascending=False)


def budget_vs_actual(expenses: pd.DataFrame, budgets: pd.DataFrame) -> pd.DataFrame:
    """One row per month and category: actual, budget, variance, variance_pct, status.

    `budgets` has category, monthly_budget, effective_from. A month uses the latest
    budget whose effective_from is on or before the month's first day, so a budget
    can change over time (rent goes up, a limit gets raised).

    variance = actual - budget, so positive means over budget. status is "over",
    "within", or "unbudgeted" (spending in a category that has no budget yet).
    """
    spent = (
        expenses.assign(month=expenses["date"].dt.to_period("M"))
        .groupby(["month", "category"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "actual"})
    )
    months = pd.period_range(expenses["date"].min(), expenses["date"].max(), freq="M")
    categories = sorted(set(spent["category"]) | set(budgets["category"]))
    grid = pd.MultiIndex.from_product([months, categories], names=["month", "category"]).to_frame(index=False)
    grid = grid.merge(spent, on=["month", "category"], how="left")
    grid["actual"] = grid["actual"].fillna(0.0)

    # Attach the budget in force for each month (as-of join on the effective date).
    grid["start"] = grid["month"].dt.start_time.astype("datetime64[ns]")
    rules = budgets[["category", "monthly_budget", "effective_from"]].copy()
    rules["effective_from"] = rules["effective_from"].astype("datetime64[ns]")
    grid = pd.merge_asof(
        grid.sort_values("start"),
        rules.sort_values("effective_from"),
        left_on="start",
        right_on="effective_from",
        by="category",
    ).rename(columns={"monthly_budget": "budget"})

    grid["variance"] = grid["actual"] - grid["budget"]
    grid["variance_pct"] = grid["variance"] / grid["budget"]
    grid["status"] = np.select(
        [grid["budget"].isna(), grid["variance"] > 0], ["unbudgeted", "over"], default="within"
    )
    keep = grid["budget"].notna() | (grid["actual"] > 0)
    columns = ["month", "category", "actual", "budget", "variance", "variance_pct", "status"]
    return grid.loc[keep, columns].sort_values(["month", "category"]).reset_index(drop=True)


def rolling_variance(bva: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """Variance vs budget over a rolling window of months, per category.

    Lumpy costs swing wildly against a monthly budget: a 1,200 quarterly premium
    against a 400 monthly budget reads as -100%, -100%, +200%. Summing actual and
    budget over a window compares like with like. Months before a full window, and
    categories with no budget, are left out.
    """
    parts = []
    for _, rows in bva.sort_values("month").groupby("category"):
        rows = rows.copy()
        rows["actual"] = rows["actual"].rolling(window).sum()
        rows["budget"] = rows["budget"].rolling(window).sum()
        parts.append(rows)
    rolled = pd.concat(parts, ignore_index=True).dropna(subset=["budget"])
    rolled["variance"] = rolled["actual"] - rolled["budget"]
    rolled["variance_pct"] = rolled["variance"] / rolled["budget"]
    columns = ["month", "category", "actual", "budget", "variance", "variance_pct"]
    return rolled[columns].sort_values(["month", "category"]).reset_index(drop=True)


def budget_summary(bva: pd.DataFrame) -> pd.DataFrame:
    """Totals per category over the months in `bva`, biggest overspend first.

    Categories with no budget at all have budget, variance and variance_pct empty
    and sort last.
    """
    summary = (
        bva.groupby("category")
        .agg(budget=("budget", lambda s: s.sum(min_count=1)), actual=("actual", "sum"))
        .reset_index()
    )
    summary["variance"] = summary["actual"] - summary["budget"]
    summary["variance_pct"] = summary["variance"] / summary["budget"]
    return summary.sort_values("variance", ascending=False, na_position="last").reset_index(drop=True)
