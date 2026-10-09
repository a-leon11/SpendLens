"""Seeded synthetic data for SpendLens.

Run `python -m spendlens.sample_data --force` to regenerate the CSVs in data/.

Income and expenses are in MXN. Investment buy prices are in USD and are
synthetic (random walks from rough October 2023 price levels), not real
market history.

Patterns are planted on purpose so the analysis has something real to find
(offsets are months from the start, 0-based):
  - payroll raises after months 12 and 24, and a December aguinaldo each year
  - rent increases after months 12 and 24
  - a Spotify price increase (month 14) and a Netflix price increase (month 26)
  - a duplicate Netflix charge (month 7)
  - subscriptions that start and stop: Disney+ (months 5 to 17), a language app (from month 22)
  - quarterly insurance and a yearly domain renewal
  - one-off expenses: laptop repair (8), flights (15), dental emergency (19), phone replacement (29)
  - seasonal electricity bills (higher April to October)
  - budgets whose Housing line follows the rent increases, and no budget for Travel
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

from spendlens.data import REPO_ROOT, SCHEMAS

DEFAULT_START = "2023-10"
DEFAULT_MONTHS = 36
DEFAULT_SEED = 42

GROCERY_STORES = ["Soriana", "HEB", "Walmart", "Oxxo"]
DINING = ["Taqueria", "Starbucks", "Pizza night", "Cafe", "Lunch out"]
SHOPPING = ["Online order", "Clothing", "Electronics accessory", "Home goods"]
ENTERTAINMENT = ["Cinema", "Concert ticket", "Game purchase", "Streaming rental"]
COURSE_PRICES = [249.0, 299.0, 399.0]

PAYROLL_BY_YEAR = (9_500.0, 11_500.0, 12_500.0)  # per payday; paid twice a month
RENT_BY_YEAR = (6_500.0, 6_900.0, 7_300.0)

# month offset -> (description, amount, category)
ONE_OFFS = {
    8: ("Laptop repair", 4800.0, "Shopping"),
    15: ("Flight tickets", 6200.0, "Travel"),
    19: ("Dental emergency", 3500.0, "Health"),
    29: ("Phone replacement", 9800.0, "Shopping"),
}
ONE_OFF_DAY = 14

# category -> monthly budget in MXN. Housing is added separately because it changes.
BUDGETS = {
    "Utilities": 1_400.0,
    "Groceries": 3_300.0,
    "Dining Out": 1_300.0,
    "Transport": 900.0,
    "Subscriptions": 500.0,
    "Health": 600.0,
    "Entertainment": 600.0,
    "Shopping": 1_000.0,
    "Education": 150.0,
    "Insurance": 400.0,
}

START_PRICES = {"VOO": 380.0, "QQQ": 355.0, "MSFT": 330.0, "AAPL": 175.0, "GOOGL": 138.0}
OTHER_TICKERS = ["QQQ", "MSFT", "AAPL", "GOOGL"]


class SampleData(NamedTuple):
    income: pd.DataFrame
    expenses: pd.DataFrame
    investments: pd.DataFrame
    budgets: pd.DataFrame


def _date(month: pd.Period, day: int) -> pd.Timestamp:
    """Day of month, clamped to the month's length (31 becomes the last day)."""
    return pd.Timestamp(year=month.year, month=month.month, day=min(day, month.days_in_month))


def _money(value: float) -> float:
    return round(float(value), 2)


def _by_year(values: tuple[float, ...], month_offset: int) -> float:
    return values[min(month_offset // 12, len(values) - 1)]


def injected_anomalies(
    start: str = DEFAULT_START, months: int = DEFAULT_MONTHS
) -> list[tuple[pd.Timestamp, str]]:
    """(date, description) of every planted one-off expense, for testing the detector."""
    periods = pd.period_range(start=start, periods=months, freq="M")
    return [(_date(periods[i], ONE_OFF_DAY), ONE_OFFS[i][0]) for i in sorted(ONE_OFFS) if i < months]


def generate(
    seed: int = DEFAULT_SEED,
    start: str = DEFAULT_START,
    months: int = DEFAULT_MONTHS,
) -> SampleData:
    """Return income, expenses, investments and budgets matching data.SCHEMAS."""
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
        payroll = _by_year(PAYROLL_BY_YEAR, i)
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
        spend(month, 1, "Rent", _by_year(RENT_BY_YEAR, i), "Housing")
        spend(month, 5, "Internet", 449.0, "Utilities")
        spend(month, 8, "Phone plan", 299.0, "Utilities")
        spend(month, 10, "Water bill", rng.normal(190, 25), "Utilities")
        if month.month % 2 == 0:
            base = 900.0 if month.month in (4, 6, 8, 10) else 450.0
            spend(month, 12, "Electricity bill", rng.normal(base, base * 0.12), "Utilities")

        # --- subscriptions: some start, some stop, some change price
        spend(month, 3, "Netflix", 219.0 if i < 26 else 249.0, "Subscriptions")
        if i == 7:
            spend(month, 4, "Netflix", 219.0, "Subscriptions")  # duplicate charge
        spend(month, 12, "Spotify", 129.0 if i < 14 else 149.0, "Subscriptions")
        spend(month, 18, "Cloud storage", 49.0, "Subscriptions")
        if 5 <= i <= 17:
            spend(month, 22, "Disney+", 159.0, "Subscriptions")  # cancelled after month 17
        if i >= 22:
            spend(month, 25, "Language app", 149.0, "Subscriptions")  # newer subscription
        if month.month == 6:
            spend(month, 9, "Domain renewal", 349.0, "Subscriptions")  # yearly
        if i % 3 == 1:
            spend(month, 6, "Insurance premium", 1_200.0, "Insurance")  # quarterly
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
            spend(month, ONE_OFF_DAY, description, cost, category)

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

    # --- budgets: constant per category, except Housing which follows the rent
    first_day = periods[0].start_time
    budget_rows = [(category, value, first_day) for category, value in BUDGETS.items()]
    for year, rent in enumerate(RENT_BY_YEAR):
        if year * 12 < months:
            budget_rows.append(("Housing", rent, periods[year * 12].start_time))

    income = pd.DataFrame(income_rows, columns=SCHEMAS["income"]["columns"])
    expenses = pd.DataFrame(expense_rows, columns=SCHEMAS["expenses"]["columns"])
    investments = pd.DataFrame(lots, columns=SCHEMAS["investments"]["columns"])
    budgets = pd.DataFrame(budget_rows, columns=SCHEMAS["budgets"]["columns"])
    return SampleData(
        income.sort_values("date", kind="stable").reset_index(drop=True),
        expenses.sort_values("date", kind="stable").reset_index(drop=True),
        investments.sort_values("buy_date", kind="stable").reset_index(drop=True),
        budgets.sort_values(["category", "effective_from"]).reset_index(drop=True),
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
    """Write the CSVs. Refuses to overwrite existing files unless force=True."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = {name: out_dir / schema["file"] for name, schema in SCHEMAS.items()}

    existing = [p.name for p in targets.values() if p.exists()]
    if existing and not force:
        raise FileExistsError(f"{existing} already exist in {out_dir}. Use --force to overwrite.")

    sample = generate(seed, start, months)
    _write(sample.income, targets["income"], {"amount": "{:.2f}"})
    _write(sample.expenses, targets["expenses"], {"amount": "{:.2f}"})
    _write(sample.investments, targets["investments"], {"shares": "{:.4f}", "buy_price": "{:.2f}"})
    _write(sample.budgets, targets["budgets"], {"monthly_budget": "{:.2f}"})
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
