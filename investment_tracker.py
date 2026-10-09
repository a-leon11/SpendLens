"""Print portfolio positions. Usage: python investment_tracker.py

Uses live prices from yfinance when reachable and falls back to cost basis
for any ticker without one (the price_source column says which).
"""
from spendlens import data, portfolio


def main() -> None:
    investments = data.load_investments()
    prices = portfolio.fetch_prices(investments["ticker"])
    positions = portfolio.build_positions(investments, prices)

    columns = ["ticker", "shares", "avg_cost", "current_price", "value",
               "unrealized_gain", "return_pct", "price_source"]
    print(f"Portfolio positions (USD). Data: {data.resolve_data_dir()}\n")
    print(positions[columns].to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    total_cost = positions["cost"].sum()
    total_value = positions["value"].sum()
    print(f"\nCost basis:    {total_cost:,.2f}")
    print(f"Current value: {total_value:,.2f}")
    if positions["price_source"].eq("live").all():
        print(f"Unrealized:    {total_value - total_cost:,.2f}")
    else:
        missing = positions.loc[positions["price_source"] != "live", "ticker"].tolist()
        print(f"Unrealized:    n/a (no live price for {', '.join(missing)})")


if __name__ == "__main__":
    main()
