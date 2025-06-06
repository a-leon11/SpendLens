import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# Load data from the data folder
income_df = pd.read_csv("data/income.csv")
expenses_df = pd.read_csv("data/expenses.csv")
investments_df = pd.read_csv("data/investments.csv")

st.title("📊 Personal Finance Dashboard")

# --- Income Section ---
st.header("💵 Income Summary")
total_income = income_df["amount"].sum()
st.metric("Total Income", f"${total_income:,.2f}")

# --- Expenses Section ---
st.header("💸 Expense Summary")
total_expenses = expenses_df["amount"].sum()
st.metric("Total Expenses", f"${total_expenses:,.2f}")

category_totals = expenses_df.groupby("category")["amount"].sum()

fig1, ax1 = plt.subplots()
ax1.pie(category_totals, labels=category_totals.index, autopct="%1.1f%%", startangle=90)
ax1.axis("equal")
st.pyplot(fig1)

# --- Investment Section ---
st.header("📈 Investment Portfolio")
st.write(investments_df)

if "value" in investments_df.columns and "ticker" in investments_df.columns:
    fig2, ax2 = plt.subplots()
    ax2.pie(investments_df["value"], labels=investments_df["ticker"], autopct="%1.1f%%")
    ax2.axis("equal")
    st.pyplot(fig2)
