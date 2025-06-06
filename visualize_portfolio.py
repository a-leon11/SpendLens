import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd

# Sample portfolio 
portfolio = {
    'AAPL': {'shares': 5},
    'MSFT': {'shares': 2},
    'GOOGL': {'shares': 3},
}

# Download current prices
def get_current_prices(tickers):
    data = yf.download(tickers, period="1d", auto_adjust=True)

    # If multiple tickers, handle MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        data = data['Close']
    else:
        data = data[['Close']]

    return data.iloc[0]

tickers = list(portfolio.keys())
current_prices = get_current_prices(tickers)

# Calculate market values
market_values = []
for ticker in tickers:
    shares = portfolio[ticker]['shares']
    value = shares * current_prices[ticker]
    market_values.append(value)

# Plot pie chart
plt.figure(figsize=(7, 7))
plt.pie(market_values, labels=tickers, autopct='%1.1f%%', startangle=140)
plt.title('Current Portfolio Allocation')
plt.axis('equal')  # Equal aspect ratio ensures pie is drawn as a circle
plt.tight_layout()
plt.show()
