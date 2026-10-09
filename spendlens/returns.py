"""Investment returns: XIRR, the annualised money-weighted return."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def xirr(cashflows: Iterable[tuple[pd.Timestamp, float]]) -> float | None:
    """Annualised rate that makes the net present value of dated cash flows zero.

    Money you put in is negative, money you get back (or the current value) is
    positive. Uses a 365-day year like Excel's XIRR and solves by bisection, so
    it needs no extra libraries. Returns None when no rate exists (all flows the
    same sign, or no sign change in the search range of -99% to +1000%).
    """
    flows = [(pd.Timestamp(date), float(value)) for date, value in cashflows]
    amounts = np.array([value for _, value in flows])
    if len(flows) < 2 or not ((amounts < 0).any() and (amounts > 0).any()):
        return None

    first = min(date for date, _ in flows)
    years = np.array([(date - first).days / 365.0 for date, _ in flows])

    def npv(rate: float) -> float:
        return float(np.sum(amounts / (1.0 + rate) ** years))

    low, high = -0.99, 10.0
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if npv_low * npv_mid <= 0:
            high = mid
        else:
            low, npv_low = mid, npv_mid
    return (low + high) / 2


def portfolio_xirr(
    investments: pd.DataFrame,
    prices: dict[str, float],
    as_of: pd.Timestamp | str | None = None,
) -> float | None:
    """XIRR of the whole portfolio: every purchase lot in, current market value out.

    Returns None unless every ticker has a live price. Valuing a position at cost
    would just report roughly 0% and look like a real result.
    """
    if not set(investments["ticker"]) <= set(prices):
        return None
    end = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()

    flows = [(lot.buy_date, -lot.shares * lot.buy_price) for lot in investments.itertuples()]
    shares = investments.groupby("ticker")["shares"].sum()
    flows.append((end, float(sum(shares[ticker] * prices[ticker] for ticker in shares.index))))
    return xirr(flows)
