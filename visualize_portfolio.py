"""Save a portfolio allocation chart. Usage: python visualize_portfolio.py [--show]"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from spendlens import data, portfolio


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio allocation chart.")
    parser.add_argument("--out", default="images/portfolio_allocation.png")
    parser.add_argument("--show", action="store_true", help="open a window instead of only saving")
    args = parser.parse_args()

    investments = data.load_investments()
    prices = portfolio.fetch_prices(investments["ticker"])
    positions = portfolio.build_positions(investments, prices)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(positions["value"], labels=positions["ticker"], autopct="%1.1f%%", startangle=140)
    ax.set_title("Portfolio allocation")
    if positions["price_source"].ne("live").any():
        fig.text(0.5, 0.02, "Some positions valued at cost basis (no live price)",
                 ha="center", fontsize=9)
    fig.tight_layout()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"saved {out}")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
