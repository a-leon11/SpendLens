"""Flag unusually large one-off expenses.

Method: a robust z-score, 0.6745 * (amount - median) / MAD, where MAD is the median
absolute deviation. Median and MAD barely move when an outlier is present, unlike
mean and standard deviation, so a 4,800 laptop repair cannot hide itself by
inflating the spread. Each transaction is compared with its own category when the
category has enough transactions, otherwise with all spending.

Recurring charges (rent, subscriptions) are left out: their changes are reported by
recurring.analyze_recurring, not as anomalies.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

OUTPUT_COLUMNS = ["date", "description", "category", "amount", "typical", "multiple", "robust_z", "reference"]


def flag_anomalies(
    expenses: pd.DataFrame,
    exclude: Iterable[str] = (),
    threshold: float = 3.5,
    min_group: int = 8,
    min_multiple: float = 3.0,
) -> pd.DataFrame:
    """Transactions that are far above what is typical, largest deviation first.

    exclude:      descriptions to skip (pass the recurring ones)
    threshold:    robust z-score needed to flag (3.5 is the usual convention)
    min_group:    transactions a category needs to be its own reference group
    min_multiple: also require amount >= this many times the typical amount. This
                  is a business rule on top of the statistics: a purchase can sit
                  3.7 robust deviations out and still only be 2.4x the usual, which
                  is not worth an alert. 2.0 flagged one ordinary 496 café bill in
                  the sample data; 3.0 does not.
    """
    candidates = expenses.loc[~expenses["description"].isin(set(exclude))].copy()
    if candidates.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    amount = candidates["amount"]
    overall_median = amount.median()
    overall_mad = (amount - overall_median).abs().median()

    grouped = amount.groupby(candidates["category"])
    category_median = grouped.transform("median")
    category_mad = (amount - category_median).abs().groupby(candidates["category"]).transform("median")
    use_category = grouped.transform("size") >= min_group

    typical = category_median.where(use_category, overall_median)
    mad = category_mad.where(use_category, overall_mad)
    candidates["typical"] = typical
    candidates["reference"] = np.where(use_category, "category", "all spending")

    z = 0.6745 * (amount - typical) / mad.replace(0, np.nan)
    # MAD of zero means every comparable amount is identical: anything bigger is an outlier.
    z = z.where(mad != 0, pd.Series(np.where(amount > typical, np.inf, 0.0), index=amount.index))
    candidates["robust_z"] = z.clip(upper=99.0)
    candidates["multiple"] = amount / typical

    flagged = candidates[(candidates["robust_z"] >= threshold) & (candidates["multiple"] >= min_multiple)]
    return flagged[OUTPUT_COLUMNS].sort_values("robust_z", ascending=False).reset_index(drop=True)
