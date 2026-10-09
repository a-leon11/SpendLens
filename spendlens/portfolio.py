"""Portfolio positions from purchase lots, with live prices when available."""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def fetch_prices(tickers: Iterable[str]) -> dict[str, float]:
    """Latest close per ticker from yfinance.

    Tickers that cannot be fetched (offline, delisted, rate-limited) are left
    out of the result; build_positions() then falls back to cost basis for them.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {}

    prices: dict[str, float] = {}
    for ticker in sorted(set(tickers)):
        try:
            closes = yf.Ticker(ticker).history(period="5d")["Close"].dropna()
        except Exception:
            continue
        if not closes.empty:
            prices[ticker] = float(closes.iloc[-1])
    return prices


def build_positions(investments: pd.DataFrame, prices: dict[str, float]) -> pd.DataFrame:
    """Collapse purchase lots into one row per ticker.

    `value` is market value when a live price exists, otherwise cost basis;
    `price_source` says which one you are looking at.
    """
    lots = investments.assign(cost=investments["shares"] * investments["buy_price"])
    positions = (
        lots.groupby("ticker")
        .agg(shares=("shares", "sum"), cost=("cost", "sum"), first_buy=("buy_date", "min"))
        .reset_index()
    )
    positions["avg_cost"] = positions["cost"] / positions["shares"]
    positions["current_price"] = positions["ticker"].map(prices)

    live = positions["current_price"].notna()
    positions["market_value"] = (positions["shares"] * positions["current_price"]).where(live)
    positions["value"] = positions["market_value"].where(live, positions["cost"])
    positions["unrealized_gain"] = positions["market_value"] - positions["cost"]
    positions["return_pct"] = positions["unrealized_gain"] / positions["cost"] * 100
    positions["price_source"] = live.map({True: "live", False: "cost basis"})
    return positions.sort_values("value", ascending=False).reset_index(drop=True)
