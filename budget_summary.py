"""Print a monthly budget summary. Usage: python budget_summary.py"""
import pandas as pd

from spendlens import budget, data


def main() -> None:
    income = data.load_income()
    expenses = data.load_expenses()

    table = budget.monthly_summary(income, expenses)
    table["savings_rate"] = table["savings_rate"].map(
        lambda rate: "n/a" if pd.isna(rate) else f"{rate:.0%}"
    )

    print(f"Monthly budget summary (MXN). Data: {data.resolve_data_dir()}\n")
    print(table.to_string(float_format=lambda value: f"{value:,.2f}"))

    print("\nSpending by category (MXN)\n")
    print(budget.category_breakdown(expenses).to_string(float_format=lambda value: f"{value:,.2f}"))


if __name__ == "__main__":
    main()
