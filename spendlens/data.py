"""Load and validate SpendLens CSV data.

Sample data lives in data/. Real data goes in data/private/, which is
gitignored and takes priority when present. Set SPENDLENS_DATA_DIR to point
somewhere else entirely.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR_ENV = "SPENDLENS_DATA_DIR"

SCHEMAS: dict[str, dict] = {
    "income": {
        "file": "income.csv",
        "columns": ["date", "source", "amount", "category"],
        "dates": ["date"],
        "numbers": ["amount"],
    },
    "expenses": {
        "file": "expenses.csv",
        "columns": ["date", "description", "amount", "category"],
        "dates": ["date"],
        "numbers": ["amount"],
    },
    "investments": {
        "file": "investments.csv",
        "columns": ["ticker", "shares", "buy_price", "buy_date"],
        "dates": ["buy_date"],
        "numbers": ["shares", "buy_price"],
    },
}


def resolve_data_dir() -> Path:
    """Env var first, then data/private/ if it has data, then data/."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    private = REPO_ROOT / "data" / "private"
    if (private / "expenses.csv").exists():
        return private
    return REPO_ROOT / "data"


def load_table(name: str, data_dir: Path | str | None = None) -> pd.DataFrame:
    """Read one table, check its columns, and parse dates (YYYY-MM-DD) and numbers."""
    schema = SCHEMAS[name]
    directory = Path(data_dir) if data_dir else resolve_data_dir()
    path = directory / schema["file"]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Generate sample data with "
            "`python -m spendlens.sample_data` or put your CSVs in data/private/."
        )

    df = pd.read_csv(path)
    missing = [c for c in schema["columns"] if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path.name}: missing column(s) {missing}. Expected {schema['columns']}."
        )

    for col in schema["dates"]:
        df[col] = pd.to_datetime(df[col], format="ISO8601")
    for col in schema["numbers"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    return df


def load_income(data_dir: Path | str | None = None) -> pd.DataFrame:
    return load_table("income", data_dir)


def load_expenses(data_dir: Path | str | None = None) -> pd.DataFrame:
    return load_table("expenses", data_dir)


def load_investments(data_dir: Path | str | None = None) -> pd.DataFrame:
    return load_table("investments", data_dir)


if __name__ == "__main__":
    print(f"Data directory: {resolve_data_dir()}\n")
    for table in SCHEMAS:
        frame = load_table(table)
        print(f"{table}: {len(frame)} rows")
        print(frame.head(3).to_string(index=False), "\n")
