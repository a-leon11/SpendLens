"""Seeded synthetic data for SpendLens.

Run `python -m spendlens.sample_data --force` to regenerate the CSVs in data/.

Income and expenses are in MXN. Investment buy prices are in USD and are
synthetic (random walks from rough 2024 price levels), not real market history.

Patterns are injected on purpose so the analysis has something real to find:
  - a salary raise after month 12
  - a December aguinaldo (Mexican year-end bonus)
  - an annual rent increase after month 12
  - a Spotify price increase at month 15
  - a duplicate Netflix charge in month 8
  - three one-off expenses: laptop repair (month 9), flights (month 16),
    dental emergency (month 20)
  - seasonal electricity bills (higher April to October)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from spendlens.data import REPO_ROOT, SCHEMAS

DEFAULT_START = "2024-10"
DEFAULT_MONTHS = 24
DEFAULT_SEED = 42

GROCERY_STORES = ["Soriana", "HEB", "Walmart", "Oxxo"]
DINING = ["Taqueria", "Starbucks", "Pizza night", "Cafe", "Lunch out"]
SHOPPING = ["Online order", "Clothing", "Electronics accessory", "Home goods"]
ENTERTAINMENT = ["Cinema", "Concert ticket", "Game purchase", "Streaming rental"]
COURSE_PRICES = [249.0, 299.0, 399.0]

# month offset (0-based) -> (description, amount, category)
ONE_OFFS = {
    8: ("Laptop repair", 4800.0, "Shopping"),
    15: ("Flight tickets", 6200.0, "Travel"),
    19: ("Dental emergency", 3500.0, "Health"),
}

START_PRICES = {"VOO": 505.0, "QQQ": 480.0, "MSFT": 420.0, "AAPL": 230.0, "GOOGL": 170.0}
OTHER_TICKERS = ["QQQ", "MSFT", "AAPL", "GOOGL"]


def _date(month: pd.Period, day: int) -> pd.Timestamp:
    """Day of month, clamped to the month's length (31 becomes the last day)."""
    return pd.Timestamp(year=month.year, month=month.month, day=min(day, month.days_in_month))


def _money(value: float) -> float:
    return round(float(value), 2)


def generate(
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
    months: int = DEFAULT_MONTHS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (income, expenses, investments) DataFrames matching data.SCHEMAS."""
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start=start, periods=months, freq="M")
    income_rows: list[tuple] = []
    expense_rows: list[tuple] = []

    def spend(month: pd.Period, day: int, description: str, amount: float, category: str) -> None:
        expense_rows.append((_date(month, day), description, _money(amount), category))

    def day() -> int:
        return int(rng.integers(1, 29))

    def amount(mean: float, sd: float, low: float, high: float) -> float:
        return float(np.clip(rng.normal(mean, sd), low, high))

    for i, month in enumerate(periods):
        # --- income: payroll twice a month, occasional freelance, December bonus
        payroll = 9_500.0 if i < 12 else 11_500.0
        income_rows.append((_date(month, 15), "Employer payroll", payroll, "Salary"))
        income_rows.append((_date(month, 31), "Employer payroll", payroll, "Salary"))
        if month.month == 12:
            income_rows.append((_date(month, 20), "Aguinaldo", payroll, "Bonus"))
        if rng.random() < 0.45:
            income_rows.append(
                (_date(month, int(rng.integers(3, 28))), "Freelance project",
                 _money(rng.integers(1500, 6500)), "Freelance")
            )

        # --- fixed monthly costs
        spend(month, 1, "Rent", 6_500.0 if i < 12 else 6_900.0, "Housing")
        spend(month, 5, "Internet", 449.0, "Utilities")
        spend(month, 8, "Phone plan", 299.0, "Utilities")
        spend(month, 10, "Water bill", rng.normal(190, 25), "Utilities")
        if month.month % 2 == 0:
            base = 900.0 if month.month in (4, 6, 8, 10) else 450.0
            spend(month, 12, "Electricity bill", rng.normal(base, base * 0.12), "Utilities")

        # --- subscriptions and gym
        spend(month, 3, "Netflix", 219.0, "Subscriptions")
        if i == 7:
            spend(month, 4, "Netflix", 219.0, "Subscriptions")  # duplicate charge
        spend(month, 12, "Spotify", 129.0 if i < 14 else 149.0, "Subscriptions")
        spend(month, 18, "Cloud storage", 49.0, "Subscriptions")
        spend(month, 2, "Gym membership", 450.0, "Health")

        # --- variable spending
        for _ in range(int(rng.integers(4, 7))):
            store = str(rng.choice(GROCERY_STORES))
            spend(month, day(), store, amount(650, 220, 180, 1400), "Groceries")
        for _ in range(int(rng.integers(4, 9))):
            place = str(rng.choice(DINING))
            spend(month, day(), place, amount(210, 90, 70, 520), "Dining Out")
        spend(month, 1, "Transit card top-up", 200.0, "Transport")
        spend(month, 16, "Transit card top-up", 200.0, "Transport")
        for _ in range(int(rng.integers(2, 6))):
            spend(month, day(), "Ride share", amount(110, 40, 45, 260), "Transport")
        for _ in range(int(rng.integers(0, 4))):
            item = str(rng.choice(SHOPPING))
            spend(month, day(), item, amount(700, 400, 120, 2200), "Shopping")
        for _ in range(int(rng.integers(1, 4))):
            what = str(rng.choice(ENTERTAINMENT))
            spend(month, day(), what, amount(300, 150, 80, 900), "Entertainment")
        if rng.random() < 0.5:
            spend(month, day(), "Pharmacy", amount(180, 90, 60, 500), "Health")
        if rng.random() < 0.3:
            spend(month, day(), "Online course", float(rng.choice(COURSE_PRICES)), "Education")
        if month.month == 12:
            spend(month, 22, "Holiday gifts", amount(1800, 500, 800, 3000), "Shopping")

        # --- one-off events
        if i in ONE_OFFS:
            description, cost, category = ONE_OFFS[i]
            spend(month, 14, description, cost, category)

    # --- investments: monthly VOO plus occasional single-stock lots (USD)
    paths = {
        ticker: price * np.cumprod(np.exp(rng.normal(0.008, 0.04, size=months)))
        for ticker, price in START_PRICES.items()
    }
    lots: list[tuple] = []

    def buy(month: pd.Period, i: int, ticker: str, budget_usd: float, buy_day: int) -> None:
        price = float(paths[ticker][i]) * (1 + float(rng.normal(0, 0.01)))
        lots.append((ticker, round(budget_usd / price, 4), round(price, 2), _date(month, buy_day)))

    for i, month in enumerate(periods):
        buy(month, i, "VOO", float(rng.integers(60, 91)), 20)
        if rng.random() < 0.25:
            buy(month, i, str(rng.choice(OTHER_TICKERS)), float(rng.integers(40, 121)),
                int(rng.integers(5, 26)))

    income = pd.DataFrame(income_rows, columns=SCHEMAS["income"]["columns"])
    expenses = pd.DataFrame(expense_rows, columns=SCHEMAS["expenses"]["columns"])
    investments = pd.DataFrame(lots, columns=SCHEMAS["investments"]["columns"])
    return (
        income.sort_values("date", kind="stable").reset_index(drop=True),
        expenses.sort_values("date", kind="stable").reset_index(drop=True),
        investments.sort_values("buy_date", kind="stable").reset_index(drop=True),
    )


def _write(df: pd.DataFrame, path: Path, formats: dict[str, str]) -> None:
    out = df.copy()
    for column, template in formats.items():
        out[column] = out[column].map(template.format)
    out.to_csv(path, index=False, date_format="%Y-%m-%d")


def write_sample_data(
    out_dir: Path | str,
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
    months: int = DEFAULT_MONTHS,
    force: bool = False,
) -> list[Path]:
    """Write the three CSVs. Refuses to overwrite existing files unless force=True."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = {name: out_dir / schema["file"] for name, schema in SCHEMAS.items()}

    existing = [p.name for p in targets.values() if p.exists()]
    if existing and not force:
        raise FileExistsError(f"{existing} already exist in {out_dir}. Use --force to overwrite.")

    income, expenses, investments = generate(seed, start, months)
    _write(income, targets["income"], {"amount": "{:.2f}"})
    _write(expenses, targets["expenses"], {"amount": "{:.2f}"})
    _write(investments, targets["investments"], {"shares": "{:.4f}", "buy_price": "{:.2f}"})
    return list(targets.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SpendLens sample data.")
    parser.add_argument("--out", default=str(REPO_ROOT / "data"), help="output folder (default: data/)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--start", default=DEFAULT_START, help="first month, YYYY-MM")
    parser.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    parser.add_argument("--force", action="store_true", help="overwrite existing CSVs")
    args = parser.parse_args()

    try:
        paths = write_sample_data(args.out, args.seed, args.start, args.months, args.force)
    except FileExistsError as err:
        raise SystemExit(str(err))
    for path in paths:
        rows = sum(1 for _ in path.open()) - 1
        print(f"wrote {path} ({rows} rows)")


if __name__ == "__main__":
    main()
