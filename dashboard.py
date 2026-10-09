"""SpendLens dashboard. Run with: streamlit run dashboard.py"""
import streamlit as st

from spendlens import budget, data, portfolio

st.set_page_config(page_title="SpendLens", page_icon="🔍", layout="wide")


@st.cache_data
def load_all():
    return data.load_income(), data.load_expenses(), data.load_investments()


@st.cache_data(ttl=900)
def live_prices(tickers: tuple[str, ...]):
    return portfolio.fetch_prices(tickers)


st.title("🔍 SpendLens")
st.caption(f"Data folder: {data.resolve_data_dir()}")

try:
    income, expenses, investments = load_all()
except (FileNotFoundError, ValueError) as err:
    st.error(str(err))
    st.stop()

# --- Budget -----------------------------------------------------------------
monthly = budget.monthly_summary(income, expenses)
total_income = monthly["income"].sum()
total_expenses = monthly["expenses"].sum()
net = total_income - total_expenses
savings_rate = net / total_income if total_income else 0.0

st.header("Budget (MXN)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", f"{total_income:,.2f}")
c2.metric("Expenses", f"{total_expenses:,.2f}")
c3.metric("Net", f"{net:,.2f}")
c4.metric("Savings rate", f"{savings_rate:.1%}")

st.subheader("Income vs expenses by month")
chart = monthly[["income", "expenses"]].copy()
chart.index = chart.index.to_timestamp()
st.bar_chart(chart)

st.subheader("Spending by category")
st.bar_chart(budget.category_breakdown(expenses))

# --- Portfolio --------------------------------------------------------------
st.header("Portfolio (USD)")
prices = live_prices(tuple(sorted(investments["ticker"].unique())))
positions = portfolio.build_positions(investments, prices)

without_price = positions.loc[positions["price_source"] == "cost basis", "ticker"].tolist()
if without_price:
    st.warning(
        f"No live price for {', '.join(without_price)}. "
        "Those positions are valued at cost basis."
    )

total_cost = positions["cost"].sum()
total_value = positions["value"].sum()
p1, p2, p3 = st.columns(3)
p1.metric("Cost basis", f"{total_cost:,.2f}")
p2.metric("Current value", f"{total_value:,.2f}")
if without_price:
    p3.metric("Unrealized gain", "n/a")
else:
    p3.metric("Unrealized gain", f"{total_value - total_cost:,.2f}")

st.dataframe(
    positions[
        ["ticker", "shares", "avg_cost", "current_price", "value",
         "unrealized_gain", "return_pct", "price_source"]
    ],
    hide_index=True,
    column_config={
        "shares": st.column_config.NumberColumn(format="%.4f"),
        "avg_cost": st.column_config.NumberColumn("Avg cost", format="%.2f"),
        "current_price": st.column_config.NumberColumn("Price", format="%.2f"),
        "value": st.column_config.NumberColumn("Value", format="%.2f"),
        "unrealized_gain": st.column_config.NumberColumn("Gain", format="%.2f"),
        "return_pct": st.column_config.NumberColumn("Return %", format="%.1f"),
        "price_source": "Price source",
    },
)

st.subheader("Allocation by value")
st.bar_chart(positions.set_index("ticker")["value"])
