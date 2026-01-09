import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

# ===============================
# STREAMLIT CONFIG
# ===============================
st.set_page_config(page_title="📈 Trading Dashboard", layout="wide")

# ===============================
# DATABASE CONNECTION
# ===============================
engine = create_engine(
    f"mysql+mysqlconnector://{st.secrets['mysql']['user']}:"
    f"{quote_plus(st.secrets['mysql']['password'])}@"
    f"{st.secrets['mysql']['host']}:"
    f"{st.secrets['mysql']['port']}/"
    f"{st.secrets['mysql']['database']}"
)

# ===============================
# SYMBOL CONFIG (STABLE ONLY)
# ===============================
TOP_INDIA_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
}

MARKETS = {
    "India 🇮🇳": {
        "Reliance": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "Infosys": "INFY.NS",
        "Sun Pharma": "SUNPHARMA.NS",
        "Dr Reddy's": "DRREDDY.NS",
        "3M India": "3MINDIA.NS",
        "MRF": "MRF.NS",
        "Tata Steel": "TATASTEEL.NS",
        "IDFC First Bank": "IDFCFIRSTB.NS"
    }
}


PERIOD_TO_DAYS = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y"
}

# ===============================
# YAHOO → DB INSERT (SAFE)
# ===============================
def fetch_and_store(symbol, period="6mo"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
    except YFRateLimitError:
        return
    except Exception:
        return

    if df.empty:
        return

    df.reset_index(inplace=True)

    df.rename(columns={
        "Date": "timestamp",
        "Open": "open_price",
        "High": "high_price",
        "Low": "low_price",
        "Close": "close_price",
        "Volume": "volume"
    }, inplace=True)

    df["symbol"] = symbol
    df = df[
        ["symbol", "timestamp",
         "open_price", "high_price",
         "low_price", "close_price", "volume"]
    ]

    df.drop_duplicates(subset=["symbol", "timestamp"], inplace=True)
    df.to_sql("stock_prices", engine, if_exists="append", index=False)

# ===============================
# INITIAL DATA BOOTSTRAP
# ===============================
def ensure_initial_data():
    try:
        count = pd.read_sql(
            "SELECT COUNT(*) AS c FROM stock_prices",
            engine
        )["c"][0]
    except Exception:
        count = 0

    if count == 0:
        fetch_and_store("^NSEI", "6mo")
        fetch_and_store("^BSESN", "6mo")
        fetch_and_store("TCS.NS", "6mo")

ensure_initial_data()

# ===============================
# DB READ HELPERS
# ===============================
def load_stock(symbol):
    return pd.read_sql(
        f"""
        SELECT * FROM stock_prices
        WHERE symbol='{symbol}'
        ORDER BY timestamp
        """,
        engine
    )

def get_change(symbol):
    df = pd.read_sql(
        f"""
        SELECT close_price FROM stock_prices
        WHERE symbol='{symbol}'
        ORDER BY timestamp DESC
        LIMIT 2
        """,
        engine
    )

    if len(df) < 2:
        return None

    latest, prev = df.iloc[0][0], df.iloc[1][0]
    change = latest - prev
    pct = (change / prev) * 100

    return round(latest, 2), round(change, 2), round(pct, 2)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("⚙ Controls")

market = st.sidebar.selectbox("Market", MARKETS.keys())
stock_name = st.sidebar.selectbox("Stock", MARKETS[market].keys())
symbol = MARKETS[market][stock_name]

period_label = st.sidebar.selectbox("Period", PERIOD_TO_DAYS.keys())
refresh = st.sidebar.button("🔄 Refresh Data")

if refresh:
    fetch_and_store(symbol, PERIOD_TO_DAYS[period_label])

# ===============================
# MARKET SNAPSHOT
# ===============================
st.markdown("## 📊 Market Snapshot")

cols = st.columns(len(TOP_INDIA_SYMBOLS))

for col, (name, sym) in zip(cols, TOP_INDIA_SYMBOLS.items()):
    data = get_change(sym)
    with col:
        if not data:
            st.metric(name, "N/A")
        else:
            price, change, pct = data
            arrow = "🔺" if change > 0 else "🔻"
            st.metric(name, price, f"{arrow} {pct}%")

# ===============================
# LOAD SELECTED STOCK
# ===============================
df = load_stock(symbol)

if df.empty:
    st.warning("No stock data available yet.")
    st.stop()

# ===============================
# INDICATORS
# ===============================
df["SMA20"] = df["close_price"].rolling(20).mean()
df["EMA20"] = df["close_price"].ewm(span=20).mean()

# ===============================
# DASHBOARD
# ===============================
left, right = st.columns([4, 1.5])

with left:
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open_price"],
        high=df["high_price"],
        low=df["low_price"],
        close=df["close_price"]
    ))

    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["SMA20"], name="SMA 20"))
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA20"], name="EMA 20"))

    fig.update_layout(
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("### 📊 Stats")
    st.metric("Last Price", round(df["close_price"].iloc[-1], 2))
    st.metric("High", round(df["high_price"].max(), 2))
    st.metric("Low", round(df["low_price"].min(), 2))
    st.metric("Volume", int(df["volume"].iloc[-1]))

st.caption("⚡ Stable Yahoo Finance–based Trading Dashboard")
