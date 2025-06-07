# persfin-trakka

# 💸 Personal Finance Tracker

This is a 5-part personal finance tracking app designed to help users manage income, expenses, and investments — all in one place. It was built with Python, Pandas, Streamlit, Matplotlib, and YFinance.

## 🔧 Features

- ✅ Input & store income, expenses, and investments using CSV files
- ✅ Summarize monthly budgets with income, spending, and savings
- ✅ Track real-time investment performance (price, return, CAGR)
- ✅ Visualize expenses and portfolio with charts (Matplotlib + Streamlit)
- ✅ Interactive dashboard to explore your data
- ✅ Fully local, lightweight, and easy to use

## 📊 Screenshots

### Streamlit Dashboard
![image](https://github.com/user-attachments/assets/3d24b841-468a-4d82-8503-141da63f0e8d)
![image](https://github.com/user-attachments/assets/a1e90ad6-9ca9-45d8-9c1c-10852231207f)


### Expense Breakdown (Matplotlib)
![image](https://github.com/user-attachments/assets/35bc77b1-7196-43cb-aee7-273085dafde8)

## 🗂️ Project Structure

persfin-trakka/
├── data/
│ ├── income.csv
│ ├── expenses.csv
│ └── investments.csv
├── images/
│ ├── streamlit_dashboard.pdf
│ └── matplotlib_chart.png
├── dashboard.py
├── visualize_portfolio.py
├── requirements.txt
└── README.md

## 🚀 Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/your-username/persfin-trakka.git
   cd persfin-trakka

   
2. Install dependencies:
```bash
pip install -r requirements.txt
```



3. Run the dashboard:

```bash
streamlit run dashboard.py
```

Make sure your CSV files are in the ```data/``` folder and match the expected format.

📦 Requirements
```
Python 3.8+
Streamlit
Pandas
Matplotlib
YFinance
```

Install with:

```bash
pip install streamlit pandas matplotlib yfinance
```

👨‍💻 Author
Built by Alan León – as a hands-on finance/data project to showcase Python, data wrangling, visualization, and Streamlit UI skills.
