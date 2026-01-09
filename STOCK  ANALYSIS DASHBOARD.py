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
st.markdown(
    """
    <style>
    /* ---------------------------
       GLOBAL APP STYLING
    ----------------------------*/
    .stApp {
        background:
            linear-gradient(rgba(10, 15, 25, 0.88), rgba(10, 15, 25, 0.88)),
            url("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #e6edf3;
        font-family: "Inter", sans-serif;
    }

    /* ---------------------------
       SIDEBAR
    ----------------------------*/
    [data-testid="stSidebar"] {
        background: rgba(12, 15, 22, 0.96);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255,255,255,0.05);
    }

    /* Sidebar titles */
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #58a6ff;
        letter-spacing: 0.5px;
    }

    /* ---------------------------
       SELECT BOXES & BUTTONS
    ----------------------------*/
    .stSelectbox > div,
    .stButton > button {
        background: rgba(22, 27, 34, 0.85) !important;
        color: #e6edf3 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        transition: all 0.25s ease;
    }

    .stSelectbox > div:hover,
    .stButton > button:hover {
        border-color: #58a6ff !important;
        box-shadow: 0 0 12px rgba(88,166,255,0.35);
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: scale(0.97);
    }

    /* ---------------------------
       METRIC CARDS
    ----------------------------*/
    div[data-testid="metric-container"] {
        background: rgba(20, 25, 35, 0.75);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        transition: all 0.3s ease;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.6);
        border-color: rgba(88,166,255,0.5);
    }

    /* Metric labels */
    div[data-testid="metric-container"] label {
        color: #8b949e;
        font-size: 0.9rem;
    }

    /* Metric values */
    div[data-testid="metric-container"] div {
        font-size: 1.3rem;
        font-weight: 600;
    }

    /* ---------------------------
       HEADINGS
    ----------------------------*/
    h1, h2, h3 {
        color: #e6edf3;
        letter-spacing: 0.3px;
    }

    h2 {
        margin-bottom: 0.4rem;
    }

    /* ---------------------------
       CHART CONTAINER
    ----------------------------*/
    [data-testid="stPlotlyChart"] {
        background: rgba(15, 20, 30, 0.85);
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 12px 35px rgba(0,0,0,0.55);
        transition: all 0.3s ease;
    }

    [data-testid="stPlotlyChart"]:hover {
        box-shadow: 0 18px 50px rgba(0,0,0,0.75);
    }

    /* ---------------------------
       CAPTION / FOOTER
    ----------------------------*/
    .stCaption {
        color: #8b949e;
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
# SYMBOL CONFIG
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

# ===============================
# INTERVAL CONFIG (1 YEAR DEFAULT)
# ===============================
INTERVAL_CONFIG = {
    "15 Minutes": "15m",
    "1 Hour": "1h",
    "1 Day": "1d",
    "1 Week": "1wk"
}

DEFAULT_PERIOD = "1y"
st.markdown(
    """
    <style>
    /* Main background image */
    .stApp {
        background: 
            linear-gradient(rgba(10, 15, 25, 0.85), rgba(10, 15, 25, 0.85)),
            url("https://images.pexels.com/photos/7947709/pexels-photo-7947709.jpeg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #ffffff;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: rgba(15, 18, 25, 0.95);
        backdrop-filter: blur(8px);
    }

    /* Metric cards (glass effect) */
    div[data-testid="metric-container"] {
        background: rgba(20, 25, 35, 0.75);
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }

    /* Headers */
    h1, h2, h3 {
        color: #e6edf3;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================
# YAHOO → DB INSERT
# ===============================
def fetch_and_store(symbol, interval):
    try:
        df = yf.Ticker(symbol).history(
            period=DEFAULT_PERIOD,
            interval=interval
        )
    except YFRateLimitError:
        return
    except Exception:
        return

    if df.empty:
        return

    df.reset_index(inplace=True)
    df.rename(columns={
        "Datetime": "timestamp",
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
# INITIAL DATA BOOTSTRAP (DAILY)
# ===============================
def ensure_initial_data():
    try:
        count = pd.read_sql(
            "SELECT COUNT(*) AS c FROM stock_prices", engine
        )["c"][0]
    except Exception:
        count = 0

    if count == 0:
        fetch_and_store("^NSEI", "1d")
        fetch_and_store("^BSESN", "1d")
        fetch_and_store("TCS.NS", "1d")

ensure_initial_data()

# ===============================
# DB HELPERS
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
    return round(latest,2), round(latest-prev,2), round((latest-prev)/prev*100,2)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("⚙ Controls")

market = st.sidebar.selectbox("Market", MARKETS.keys())
stock_name = st.sidebar.selectbox("Stock", MARKETS[market].keys())
symbol = MARKETS[market][stock_name]

interval_label = st.sidebar.selectbox(
    "Interval",
    list(INTERVAL_CONFIG.keys()),
    index=2  # default = 1 Day
)

interval = INTERVAL_CONFIG[interval_label]

refresh = st.sidebar.button("🔄 Refresh Data")

if refresh:
    fetch_and_store(symbol, interval)

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
            price, chg, pct = data
            arrow = "🔺" if chg > 0 else "🔻"
            st.metric(name, price, f"{arrow} {pct}%")

# ===============================
# LOAD STOCK DATA
# ===============================
if interval in ["15m", "1h"]:
    df = pd.read_sql(
        f"""
        SELECT * FROM stock_prices
        WHERE symbol='{symbol}'
        AND timestamp >= NOW() - INTERVAL 7 DAY
        ORDER BY timestamp
        """,
        engine
    )
else:
    df = load_stock(symbol)

if df.empty:
    st.warning("No data available.")
    st.stop()

latest_price = round(df["close_price"].iloc[-1], 2)

# ===============================
# TECHNICAL INDICATORS (DAILY LOGIC)
# ===============================
df["SMA20"] = df["close_price"].rolling(20).mean()
df["SMA50"] = df["close_price"].rolling(50).mean()
df["SMA200"] = df["close_price"].rolling(200).mean()
df["EMA20"] = df["close_price"].ewm(span=20).mean()

# ===============================
# TREND ANALYSIS
# ===============================
latest = df.iloc[-1]

if latest["close_price"] > latest["SMA50"] > latest["SMA200"]:
    trend = "Bullish"
    strength = "Strong"
elif latest["close_price"] < latest["SMA50"] < latest["SMA200"]:
    trend = "Bearish"
    strength = "Strong"
else:
    trend = "Sideways"
    strength = "Weak"

support = df["low_price"].rolling(20).min().iloc[-1]
resistance = df["high_price"].rolling(20).max().iloc[-1]

# ===============================
# SHORT-TERM FORECAST
# ===============================
mean_price = df["close_price"].rolling(20).mean().iloc[-1]
std_dev = df["close_price"].rolling(20).std().iloc[-1]

forecast_low = round(mean_price - std_dev, 2)
forecast_high = round(mean_price + std_dev, 2)

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
    fig.add_hrect(
        y0=forecast_low, y1=forecast_high,
        fillcolor="green", opacity=0.08, line_width=0
    )
    fig.update_layout(
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown(f"## {stock_name}")
    st.metric("Current Price", latest_price)

    st.markdown("### 📊 Trend Analysis")
    st.metric("Trend", trend)
    st.metric("Momentum", strength)
    st.metric("Support", round(support,2))
    st.metric("Resistance", round(resistance,2))

    st.markdown("### 🔮 Statistical Forecast")
    st.metric("Expected Range", f"{forecast_low} – {forecast_high}")

st.caption("⚠ Forecast is statistical, not financial advice | DB-driven analytics")
