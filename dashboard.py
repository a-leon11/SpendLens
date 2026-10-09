"""SpendLens dashboard. Run with: streamlit run dashboard.py"""
import streamlit as st

from spendlens import anomalies, budget, charts, data, portfolio, recurring, returns

st.set_page_config(page_title="SpendLens", page_icon="🔍", layout="wide")

PERIODS = {"All time": None, "Last 12 months": 12, "Last 6 months": 6}


@st.cache_data
def load_all():
    return data.load_income(), data.load_expenses(), data.load_investments()


@st.cache_data
def load_budgets():
    try:
        return data.load_budgets()
    except FileNotFoundError:
        return None


@st.cache_data
def analyze(expenses):
    report = recurring.analyze_recurring(expenses)
    unusual = anomalies.flag_anomalies(expenses, exclude=report.items["description"])
    return report, unusual


@st.cache_data(ttl=900)
def live_prices(tickers: tuple[str, ...]):
    return portfolio.fetch_prices(tickers)


st.title("🔍 SpendLens")
st.caption(f"Data folder: {data.resolve_data_dir()}")

try:
    income_all, expenses_all, investments = load_all()
except (FileNotFoundError, ValueError) as err:
    st.error(str(err))
    st.stop()

# The period filter drives the budget and cash-flow views. Recurring-charge and
# anomaly detection always look at the full history: they need it to see patterns.
last_date = max(income_all["date"].max(), expenses_all["date"].max())
period = st.sidebar.radio("Period", list(PERIODS))
st.sidebar.caption(f"Data through {last_date:%b %Y}")
window = PERIODS[period]
if window:
    start = (last_date.to_period("M") - (window - 1)).start_time
    income = income_all[income_all["date"] >= start]
    expenses = expenses_all[expenses_all["date"] >= start]
else:
    income, expenses = income_all, expenses_all

overview, budget_tab, recurring_tab, portfolio_tab = st.tabs(
    ["Overview", "Budget vs actual", "Recurring & alerts", "Portfolio"]
)

# --- Overview -----------------------------------------------------------------
monthly = budget.monthly_summary(income, expenses)
total_income = monthly["income"].sum()
total_expenses = monthly["expenses"].sum()
net = total_income - total_expenses
savings_rate = net / total_income if total_income else 0.0

with overview:
    st.header("Cash flow (MXN)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", f"{total_income:,.2f}")
    c2.metric("Expenses", f"{total_expenses:,.2f}")
    c3.metric("Net", f"{net:,.2f}")
    c4.metric("Savings rate", f"{savings_rate:.1%}")

    st.subheader("Income vs expenses by month")
    st.altair_chart(charts.monthly_chart(monthly))

    st.subheader("Savings rate")
    st.caption("Net saved divided by income. The 3-month average smooths out bonus and one-off months.")
    st.altair_chart(charts.savings_rate_chart(monthly))

    st.subheader("Spending by category")
    st.altair_chart(charts.category_chart(budget.category_breakdown(expenses)))

# --- Budget vs actual -----------------------------------------------------------
with budget_tab:
    st.header("Budget vs actual (MXN)")
    budgets = load_budgets()
    if budgets is None:
        st.info(
            "No budgets.csv found. Add one with the columns category, monthly_budget, "
            "effective_from to enable this tab."
        )
    else:
        bva = budget.budget_vs_actual(expenses, budgets)
        summary = budget.budget_summary(bva)
        budgeted = summary[summary["budget"].notna()]
        over = budgeted[budgeted["variance"] > 0]
        unbudgeted = summary.loc[summary["budget"].isna(), "actual"].sum()

        b1, b2, b3 = st.columns(3)
        b1.metric("Categories over budget", f"{len(over)} of {len(budgeted)}")
        b2.metric("Overspend in those categories", f"{over['variance'].sum():,.2f}")
        b3.metric("Unbudgeted spend", f"{unbudgeted:,.2f}")

        st.subheader("By category")
        st.caption("Variance is actual minus budget, so positive means over budget.")
        st.dataframe(
            summary,
            hide_index=True,
            column_config={
                "category": "Category",
                "budget": st.column_config.NumberColumn("Budget", format="%.2f"),
                "actual": st.column_config.NumberColumn("Actual", format="%.2f"),
                "variance": st.column_config.NumberColumn("Variance", format="%+.2f"),
                "variance_pct": st.column_config.NumberColumn("Variance %", format="%+.1f%%"),
            },
        )

        st.subheader("Month by month")
        view = st.radio("View", ["Rolling 3 months", "Single month"], horizontal=True)
        if view == "Rolling 3 months":
            st.caption(
                "Each cell compares the last 3 months of spending with the last 3 months of budget, "
                "so lumpy bills (a quarterly premium) do not swing wildly. Red is over budget, blue "
                "is under, capped at 50% either way."
            )
            st.altair_chart(charts.budget_heatmap(budget.rolling_variance(bva, window=3), window=3))
        else:
            st.caption(
                "Single months against a flat monthly budget. Expect extreme colours for "
                "irregular costs. Red is over budget, blue is under, capped at 50% either way."
            )
            st.altair_chart(charts.budget_heatmap(bva))

# --- Recurring charges and alerts ---------------------------------------------------
with recurring_tab:
    report, unusual = analyze(expenses_all)
    active = report.items[report.items["active"]]
    recurring_spend = recurring.recurring_spend_by_month(expenses, report.items)
    spend_total = expenses["amount"].sum()
    recurring_share = recurring_spend["amount"].sum() / spend_total if spend_total else 0.0

    st.header("Recurring charges")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Active recurring charges", f"{len(active)}")
    r2.metric("Monthly run rate (MXN)", f"{active['monthly_cost'].sum():,.2f}")
    r3.metric("Annual run rate (MXN)", f"{active['annual_cost'].sum():,.2f}")
    r4.metric("Recurring share of spend", f"{recurring_share:.0%}")

    st.caption(
        "A charge is recurring when it is billed on a regular month cadence and a stable day of "
        "the month. Run rate is what you are committed to paying, normalised to a month or a year."
    )
    st.dataframe(
        report.items.drop(columns=["charges"]),
        hide_index=True,
        column_config={
            "description": "Charge",
            "category": "Category",
            "cadence": "Cadence",
            "latest_amount": st.column_config.NumberColumn("Latest amount", format="%.2f"),
            "monthly_cost": st.column_config.NumberColumn("Per month", format="%.2f"),
            "annual_cost": st.column_config.NumberColumn("Per year", format="%.2f"),
            "first_seen": st.column_config.DateColumn("First seen"),
            "last_seen": st.column_config.DateColumn("Last seen"),
            "active": "Active",
            "variable": "Variable amount",
        },
    )

    st.subheader("Recurring spend by month")
    if not recurring_spend.empty:
        st.altair_chart(charts.recurring_spend_chart(recurring_spend))

    st.header("Alerts")
    st.subheader("Price changes")
    if report.price_changes.empty:
        st.caption("None found.")
    else:
        st.dataframe(
            report.price_changes.rename(columns={"change_pct": "change_%"}),
            hide_index=True,
            column_config={
                "description": "Charge",
                "month": "Month",
                "old_amount": st.column_config.NumberColumn("Old", format="%.2f"),
                "new_amount": st.column_config.NumberColumn("New", format="%.2f"),
                "change_%": st.column_config.NumberColumn("Change %", format="%+.1f"),
                "annual_impact": st.column_config.NumberColumn("Per year", format="%+.2f"),
            },
        )

    st.subheader("Duplicate charges")
    if report.duplicates.empty:
        st.caption("None found.")
    else:
        st.dataframe(
            report.duplicates,
            hide_index=True,
            column_config={
                "description": "Charge",
                "month": "Month",
                "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "extra_charges": "Extra charges",
                "wasted": st.column_config.NumberColumn("Possibly wasted", format="%.2f"),
            },
        )

    st.subheader("Unusual transactions")
    st.caption(
        "Flagged with a robust z-score (median and MAD, so one big purchase cannot hide itself) "
        "and at least 3x the typical amount for its category. Recurring charges are excluded."
    )
    if unusual.empty:
        st.caption("None found.")
    else:
        st.dataframe(
            unusual,
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date"),
                "description": "Description",
                "category": "Category",
                "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "typical": st.column_config.NumberColumn("Typical", format="%.2f"),
                "multiple": st.column_config.NumberColumn("x typical", format="%.1f"),
                "robust_z": st.column_config.NumberColumn("Robust z", format="%.1f"),
                "reference": "Compared with",
            },
        )

# --- Portfolio ------------------------------------------------------------------
with portfolio_tab:
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
    annualized = returns.portfolio_xirr(investments, prices)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Cost basis", f"{total_cost:,.2f}")
    p2.metric("Current value", f"{total_value:,.2f}")
    p3.metric("Unrealized gain", "n/a" if without_price else f"{total_value - total_cost:,.2f}")
    p4.metric("Annualized return (XIRR)", "n/a" if annualized is None else f"{annualized:.1%}")
    st.caption(
        "XIRR is the annual return that accounts for when each purchase was made. "
        "It needs live prices for every holding."
    )

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
    st.altair_chart(charts.allocation_chart(positions))
