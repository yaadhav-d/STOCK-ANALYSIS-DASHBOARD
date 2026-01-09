import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from datetime import datetime

# ===============================
# STREAMLIT CONFIG
# ===============================
st.set_page_config(page_title="📈 Trading Dashboard", layout="wide")

# ===============================
# DATABASE CONNECTION (UPDATED)
# ===============================
engine = create_engine(
    f"mysql+mysqlconnector://{st.secrets['mysql']['user']}:"
    f"{quote_plus(st.secrets['mysql']['password'])}@"
    f"{st.secrets['mysql']['host']}:"
    f"{st.secrets['mysql']['port']}/"
    f"{st.secrets['mysql']['database']}"
)


MARKET_BACKGROUNDS = {
    "India 🇮🇳": "https://images.unsplash.com/photo-1581092334494-5c7b3e1b5f4a",
    "USA 🇺🇸": "https://images.unsplash.com/photo-1444653614773-995cb1ef9efa"
}

# ===============================
# SYMBOL CONFIG
# ===============================
TOP_INDIA_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC BANK": "HDFCBANK.NS",
}

MARKETS = {
    "India 🇮🇳": {
        "Reliance": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "Infosys": "INFY.NS"
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
    df = yf.Ticker(symbol).history(period=period, interval="1d")

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
    df = df[[
        "symbol","timestamp",
        "open_price","high_price",
        "low_price","close_price","volume"
    ]]

    df.to_sql("stock_prices", engine, if_exists="append", index=False)

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

    return round(latest,2), round(change,2), round(pct,2)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("⚙ Controls")

market = st.sidebar.selectbox("Market", MARKETS.keys())
stock_name = st.sidebar.selectbox("Stock", MARKETS[market].keys())
symbol = MARKETS[market][stock_name]

period_label = st.sidebar.selectbox("Period", PERIOD_TO_DAYS.keys())
refresh = st.sidebar.button("🔄 Refresh Data")

# ===============================
# FORCE DB UPDATE
# ===============================
if refresh:
    fetch_and_store("^NSEI", "6mo")
    fetch_and_store("^BSESN", "6mo")
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
            color = "#00ff99" if change > 0 else "#ff4d4d"

            st.markdown(
                f"""
                <div style="padding:14px;border-radius:14px;
                            background:#0e1117;text-align:center">
                    <div style="color:#aaa">{name}</div>
                    <div style="font-size:24px;font-weight:700">{price}</div>
                    <div style="color:{color}">
                        {arrow} {pct:.2f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ===============================
# LOAD SELECTED STOCK
# ===============================
df = load_stock(symbol)

if df.empty:
    st.error("No data found. Click Refresh Data.")
    st.stop()

# ===============================
# INDICATORS
# ===============================
df["SMA20"] = df["close_price"].rolling(20).mean()
df["EMA20"] = df["close_price"].ewm(span=20).mean()

# ===============================
# DASHBOARD
# ===============================
left, right = st.columns([4,1.5])

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
    st.metric("Last Price", round(df["close_price"].iloc[-1],2))
    st.metric("High", round(df["high_price"].max(),2))
    st.metric("Low", round(df["low_price"].min(),2))
    st.metric("Volume", int(df["volume"].iloc[-1]))

st.caption("⚡ Fully DB-driven TradingView-style Dashboard")
