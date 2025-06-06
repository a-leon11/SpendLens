import pandas as pd
from pathlib import Path

# Load CSVs
data_dir = Path("data")

def load_csv(filename):
    path = data_dir / filename
    try:
        df = pd.read_csv(path, parse_dates=['date', 'buy_date'], dayfirst=True, infer_datetime_format=True)
        print(f"Loaded {filename} ✅")
        return df
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None

if __name__ == "__main__":
    income_df = load_csv("income.csv")
    expenses_df = load_csv("expenses.csv")
    investments_df = load_csv("investments.csv")

    # Print basic info
    if income_df is not None:
        print("\nIncome Preview:")
        print(income_df.head())

    if expenses_df is not None:
        print("\nExpenses Preview:")
        print(expenses_df.head())

    if investments_df is not None:
        print("\nInvestments Preview:")
        print(investments_df.head())
