"""Find recurring charges, price changes and duplicate charges in expenses.

A description counts as recurring when it is billed on a regular month cadence
(every 1, 2, 3, 6 or 12 months) and on a stable day of the month. That separates
subscriptions and bills from things you merely buy often, like groceries or rides,
which land on random days.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pandas as pd

CADENCES = {1: "monthly", 2: "every 2 months", 3: "quarterly", 6: "every 6 months", 12: "yearly"}

ITEM_COLUMNS = [
    "description", "category", "cadence", "charges", "latest_amount", "monthly_cost",
    "annual_cost", "first_seen", "last_seen", "active", "variable",
]
CHANGE_COLUMNS = ["description", "month", "old_amount", "new_amount", "change_pct", "annual_impact"]
DUPLICATE_COLUMNS = ["description", "month", "amount", "extra_charges", "wasted"]


class RecurringReport(NamedTuple):
    items: pd.DataFrame          # one row per recurring charge
    price_changes: pd.DataFrame  # amount stepped up or down
    duplicates: pd.DataFrame     # charged more times in a month than usual


def analyze_recurring(
    expenses: pd.DataFrame,
    min_months: int = 3,
    regularity: float = 0.7,
    max_day_spread: float = 3.5,
    price_tolerance: float = 0.02,
) -> RecurringReport:
    """Detect recurring charges.

    regularity:      share of gaps between charges that must equal the typical gap
    max_day_spread:  max standard deviation (days) of the billing day
    price_tolerance: smallest relative amount change counted as a price change

    A charge is "variable" (a utility bill, say) when its amount changes in more
    than half of its billings. Variable charges get no price-change alerts, and are
    only accepted at a monthly or two-monthly cadence: a fluctuating amount that
    shows up once a year (holiday gifts) is a seasonal purchase, not a bill.
    "active" means it was billed within one cadence interval of the end of the data.
    """
    df = expenses.assign(month=expenses["date"].dt.to_period("M"))
    data_end = df["month"].max()
    items: list[dict] = []
    changes: list[dict] = []
    duplicates: list[dict] = []

    for description, charges in df.groupby("description"):
        by_month = charges.groupby("month")["amount"].agg(["median", "size"]).sort_index()
        if len(by_month) < min_months:
            continue

        ordinals = np.array([m.ordinal for m in by_month.index])
        gaps = np.diff(ordinals)
        gap = int(pd.Series(gaps).mode().iloc[0])
        if gap not in CADENCES or (gaps == gap).mean() < regularity:
            continue
        if charges["date"].dt.day.std(ddof=0) > max_day_spread:
            continue

        amounts = by_month["median"].to_numpy()
        counts = by_month["size"].to_numpy()
        relative_change = np.abs(amounts[1:] / amounts[:-1] - 1)
        variable = bool((relative_change > price_tolerance).mean() > 0.5)
        if variable and gap > 2:
            continue  # fluctuating and infrequent: a seasonal purchase, not a bill

        if not variable:
            for position in np.flatnonzero(relative_change > price_tolerance) + 1:
                old, new = float(amounts[position - 1]), float(amounts[position])
                changes.append({
                    "description": description,
                    "month": str(by_month.index[position]),
                    "old_amount": old,
                    "new_amount": new,
                    "change_pct": (new / old - 1) * 100,
                    "annual_impact": (new - old) * 12 / gap,
                })

        usual = float(np.median(counts))
        for position in np.flatnonzero(counts > usual):
            extra = int(counts[position] - usual)
            duplicates.append({
                "description": description,
                "month": str(by_month.index[position]),
                "amount": float(amounts[position]),
                "extra_charges": extra,
                "wasted": float(amounts[position]) * extra,
            })

        latest = float(charges.sort_values("date")["amount"].iloc[-1])
        level = float(amounts.mean()) if variable else latest
        monthly_cost = level * usual / gap
        items.append({
            "description": description,
            "category": charges["category"].mode().iloc[0],
            "cadence": CADENCES[gap],
            "charges": len(charges),
            "latest_amount": latest,
            "monthly_cost": monthly_cost,
            "annual_cost": monthly_cost * 12,
            "first_seen": charges["date"].min(),
            "last_seen": charges["date"].max(),
            "active": bool(data_end.ordinal - by_month.index[-1].ordinal <= gap),
            "variable": variable,
        })

    item_frame = pd.DataFrame(items, columns=ITEM_COLUMNS)
    if not item_frame.empty:
        item_frame = item_frame.sort_values(["active", "annual_cost"], ascending=[False, False])
    return RecurringReport(
        item_frame.reset_index(drop=True),
        pd.DataFrame(changes, columns=CHANGE_COLUMNS),
        pd.DataFrame(duplicates, columns=DUPLICATE_COLUMNS),
    )


def recurring_spend_by_month(expenses: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Actual spend on recurring charges per month and category (for charting)."""
    recurring = expenses[expenses["description"].isin(items["description"])]
    return (
        recurring.assign(month=recurring["date"].dt.to_period("M"))
        .groupby(["month", "category"], as_index=False)["amount"]
        .sum()
    )
