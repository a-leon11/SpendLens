"""Render the README images from the committed sample data.

    python -m spendlens.figures

Needs vl-convert-python (listed in requirements-dev.txt). Always reads data/, never
data/private/, so personal numbers cannot end up in a README image. The portfolio
chart is valued at cost so the image is the same on every run and needs no network.
"""
from __future__ import annotations

from spendlens import budget, charts, data, portfolio, recurring

SAMPLE_DIR = data.REPO_ROOT / "data"
OUT_DIR = data.REPO_ROOT / "docs" / "images"
WIDTH = 900


def build_figures() -> dict:
    income = data.load_income(SAMPLE_DIR)
    expenses = data.load_expenses(SAMPLE_DIR)
    investments = data.load_investments(SAMPLE_DIR)
    budgets = data.load_budgets(SAMPLE_DIR)

    monthly = budget.monthly_summary(income, expenses)
    bva = budget.rolling_variance(budget.budget_vs_actual(expenses, budgets), window=3)
    report = recurring.analyze_recurring(expenses)
    spend = recurring.recurring_spend_by_month(expenses, report.items)
    positions = portfolio.build_positions(investments, prices={})

    return {
        "monthly": charts.monthly_chart(monthly).properties(
            title="Income vs expenses by month (MXN)"),
        "savings_rate": charts.savings_rate_chart(monthly).properties(
            title="Savings rate: monthly and 3-month average"),
        "budget_heatmap": charts.budget_heatmap(bva, window=3).properties(
            title="Spending vs budget, rolling 3 months (red = over, blue = under)"),
        "recurring_spend": charts.recurring_spend_chart(spend).properties(
            title="Recurring charges by month (MXN)"),
        "categories": charts.category_chart(budget.category_breakdown(expenses)).properties(
            title="Spending by category (MXN)"),
        "allocation": charts.allocation_chart(positions).properties(
            title="Portfolio allocation by cost (USD)"),
    }


def main() -> None:
    try:
        import vl_convert  # noqa: F401  (Altair uses it to write PNGs)
    except ImportError:
        raise SystemExit("Install the dev requirements first: pip install -r requirements-dev.txt")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, chart in build_figures().items():
        path = OUT_DIR / f"{name}.png"
        chart.properties(width=WIDTH).save(path, scale_factor=2)
        print(f"wrote {path.relative_to(data.REPO_ROOT)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
