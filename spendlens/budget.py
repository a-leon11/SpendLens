"""Monthly budget summaries from income and expense tables."""
from __future__ import annotations

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
