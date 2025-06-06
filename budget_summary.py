import pandas as pd
from pathlib import Path

# Load CSVs
data_dir = Path("data")
income_df = pd.read_csv(data_dir / "income.csv", parse_dates=["date"])
expenses_df = pd.read_csv(data_dir / "expenses.csv", parse_dates=["date"])

# Add a month column
income_df["month"] = income_df["date"].dt.to_period("M")
expenses_df["month"] = expenses_df["date"].dt.to_period("M")

# Summarize by month
monthly_income = income_df.groupby("month")["amount"].sum()
monthly_expenses = expenses_df.groupby("month")["amount"].sum()
monthly_savings = monthly_income - monthly_expenses

# Print budget summary
print("📊 Monthly Budget Summary:\n")
for month in monthly_income.index:
    print(f"🗓️ {month}")
    print(f"  Income:      ${monthly_income[month]:.2f}")
    print(f"  Expenses:    ${monthly_expenses.get(month, 0):.2f}")
    print(f"  Net Savings: ${monthly_savings[month]:.2f}")
    print("")

# Optional: Breakdown of expenses by category
print("🔍 Expense Breakdown by Category:\n")
category_breakdown = expenses_df.groupby("category")["amount"].sum()
print(category_breakdown.sort_values(ascending=False))
