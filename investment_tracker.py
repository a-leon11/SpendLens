import pandas as pd
import yfinance as yf
from pathlib import Path

# Load investment data
data_dir = Path("data")
investments = pd.read_csv(data_dir / "investments.csv", parse_dates=["buy_date"])

# Fetch live prices using yfinance
def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.history(period="1d")["Close"].iloc[-1]
    except:
        return None

# Add current price and market value
investments["current_price"] = investments["ticker"].apply(get_current_price)
investments["market_value"] = investments["shares"] * investments["current_price"]
investments["initial_value"] = investments["shares"] * investments["buy_price"]
investments["unrealized_gain"] = investments["market_value"] - investments["initial_value"]

# Print results
print("📈 Investment Portfolio Summary:\n")
print(investments[["ticker", "shares", "buy_price", "current_price", "market_value", "unrealized_gain"]])

print("\n💰 Total Market Value: ${:.2f}".format(investments["market_value"].sum()))
print("📉 Total Unrealized Gain/Loss: ${:.2f}".format(investments["unrealized_gain"].sum()))
