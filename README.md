# SpendLens

Personal finance analytics, managed like cloud spend: see where the money goes, budget against it, and track what you invest. Local-first, CSV in, dashboard out.

**Status: early.** The foundations work (clean data loading, monthly budget, portfolio positions, dashboard). The deeper analysis is on the roadmap below.

## What works today

- Monthly budget summary: income, expenses, net, savings rate
- Spending breakdown by category
- Portfolio positions built from purchase lots, valued with live prices from yfinance, with an automatic cost-basis fallback when a price is unavailable
- Streamlit dashboard over all of the above
- Schema-checked CSV loading with clear errors instead of silent failures
- Seeded sample data (24 months, about 700 transactions) so everything has something to show on first run

## Quick start

Tested on Python 3.13; should work on 3.10+.

```bash
git clone https://github.com/a-leon11/spendlens.git
cd spendlens
pip install -r requirements.txt
streamlit run dashboard.py
```

Other commands:

| Command | What it does |
|---|---|
| `python budget_summary.py` | Monthly budget table and category totals in the terminal |
| `python investment_tracker.py` | Portfolio positions in the terminal |
| `python visualize_portfolio.py` | Saves an allocation chart to `images/` |
| `python -m spendlens.sample_data --force` | Regenerates the sample CSVs in `data/` |
| `pip install -r requirements-dev.txt && pytest` | Runs the tests |

## Data

The CSVs in `data/` are **synthetic**. Income and expenses are in MXN. Investment buy prices are in USD and are generated, not real market history.

**Use your own data:** put real CSVs in `data/private/`. That folder is gitignored and takes priority over `data/`, so your finances never reach the repo. You can also point `SPENDLENS_DATA_DIR` at any folder.

Dates are `YYYY-MM-DD`.

| File | Columns |
|---|---|
| `income.csv` | `date, source, amount, category` |
| `expenses.csv` | `date, description, amount, category` |
| `investments.csv` | `ticker, shares, buy_price, buy_date` (one row per purchase lot) |

The sample data includes a few patterns on purpose for the analysis to find: a duplicate Netflix charge, a Spotify price increase, an annual rent increase, three one-off expenses, a salary raise and a December bonus. They are listed in `spendlens/sample_data.py`.

## Project structure

```
spendlens/
├── data.py           # schema-checked CSV loaders
├── budget.py         # monthly summary, category breakdown
├── portfolio.py      # positions from lots, live prices with fallback
└── sample_data.py    # seeded synthetic data generator
dashboard.py          # Streamlit app
budget_summary.py     # terminal budget report
investment_tracker.py # terminal portfolio report
visualize_portfolio.py
tests/
data/                 # synthetic sample CSVs
```

## Roadmap

- [ ] Budget vs actual per category, with variance
- [ ] Recurring-charge detection, duplicate and price-increase flags
- [ ] Spending anomaly detection
- [ ] Portfolio CAGR / XIRR and benchmark comparison
- [ ] MXN/USD handling across budget and portfolio
- [ ] Bank CSV import
- [ ] CI, license, and fresh screenshots

## Tech

Python, pandas, Streamlit, Matplotlib, yfinance, pytest.
