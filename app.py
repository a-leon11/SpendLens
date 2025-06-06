import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

st.set_page_config(page_title="Personal Finance Tracker", layout="wide")

st.title("📊 Personal Finance Dashboard")
st.write("Track your income, expenses, savings, and investments with live updates.")

# Upload CSVs
st.sidebar.header("Upload your data")
income_file = st.sidebar.file_uploader("Income CSV", type="csv")
expenses_file = st.sidebar.file_uploader("Expenses CSV", type="csv")
investments_file = st.sidebar.file_uploader("Investments CSV", type="csv")

# Load and show uploaded data
if income_file and expenses_file and investments_file:
    income_df = pd.read_csv(income_file)
    expenses_df = pd.read_csv(expenses_file)
    investments_df = pd.read_csv(investments_file)

    st.subheader("Data Preview")
    st.write("**Income Data**")
    st.dataframe(income_df)
    st.write("**Expenses Data**")
    st.dataframe(expenses_df)
    st.write("**Investments Data**")
    st.dataframe(investments_df)

    # Budget Summary
    total_income = income_df['Amount'].sum()
    total_expenses = expenses_df['Amount'].sum()
    savings = total_income - total_expenses

    st.metric("💰 Total Income", f"${total_income:,.2f}")
    st.metric("🧾 Total Expenses", f"${total_expenses:,.2f}")
    st.metric("💸 Savings", f"${savings:,.2f}")

    # Investments Summary with yfinance
    st.subheader("Investment Portfolio")
    portfolio = dict(zip(investments_df['Ticker'], investments_df['Shares']))
    tickers = list(portfolio.keys())
    prices = yf.download(tickers, period="1d", progress=False)['Close'].iloc[0]
    market_values = [portfolio[ticker] * prices[ticker] for ticker in tickers]

    fig, ax = plt.subplots()
    ax.pie(market_values, labels=tickers, autopct='%1.1f%%')
    ax.set_title("Current Portfolio Allocation")
    st.pyplot(fig)

else:
    st.warning("⬅️ Upload all three CSV files to get started.")
