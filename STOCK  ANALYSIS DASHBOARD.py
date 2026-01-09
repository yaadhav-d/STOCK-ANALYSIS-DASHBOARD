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
    /* =========================
       STICKY RIGHT PANEL
    ==========================*/
    .sticky-panel {
        position: sticky;
        top: 80px;
    }

    /* =========================
       TREND GLOW STATES
    ==========================*/
    .bullish {
        box-shadow: 0 0 25px rgba(0, 255, 120, 0.35);
        border: 1px solid rgba(0, 255, 120, 0.45);
    }

    .bearish {
        box-shadow: 0 0 25px rgba(255, 70, 70, 0.35);
        border: 1px solid rgba(255, 70, 70, 0.45);
    }

    .sideways {
        box-shadow: 0 0 25px rgba(88, 166, 255, 0.35);
        border: 1px solid rgba(88, 166, 255, 0.45);
    }

    /* =========================
       KPI ANIMATION
    ==========================*/
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.03); }
        100% { transform: scale(1); }
    }

    .pulse {
        animation: pulse 1.5s ease-in-out;
    }

    /* =========================
       BADGES
    ==========================*/
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        margin-right: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    /* =========================
       GLOBAL BACKGROUND
    ==========================*/
    .stApp {
        background:
            linear-gradient(rgba(12, 18, 28, 0.9), rgba(12, 18, 28, 0.9)),
            url("https://images.pexels.com/photos/7947709/pexels-photo-7947709.jpeg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #e6edf3;
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont;
    }

    /* =========================
       SIDEBAR
    ==========================*/
    section[data-testid="stSidebar"] {
        background: rgba(15, 20, 30, 0.97);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    section[data-testid="stSidebar"] * {
        color: #e6edf3;
    }

    /* =========================
       HEADINGS
    ==========================*/
    h1, h2, h3 {
        color: #f0f6fc;
        letter-spacing: 0.4px;
    }

    /* =========================
       SELECTBOX / INPUTS
    ==========================*/
    div[data-baseweb="select"] > div {
        background-color: rgba(22, 27, 34, 0.85) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        transition: all 0.2s ease-in-out;
    }

    div[data-baseweb="select"]:hover > div {
        border-color: #58a6ff !important;
        box-shadow: 0 0 12px rgba(88,166,255,0.35);
    }

    /* =========================
       BUTTONS
    ==========================*/
    button {
        background: rgba(22, 27, 34, 0.9) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #e6edf3 !important;
        transition: all 0.2s ease-in-out;
    }

    button:hover {
        border-color: #58a6ff !important;
        box-shadow: 0 0 14px rgba(88,166,255,0.4);
        transform: translateY(-1px);
    }

    button:active {
        transform: scale(0.96);
    }

    /* =========================
       METRIC CARDS
    ==========================*/
    div[data-testid="metric-container"] {
        background: rgba(22, 27, 34, 0.75);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 10px 30px rgba(0,0,0,0.45);
        transition: all 0.25s ease;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 45px rgba(0,0,0,0.65);
        border-color: rgba(88,166,255,0.45);
    }

    /* Metric label */
    div[data-testid="metric-container"] label {
        color: #8b949e;
        font-size: 0.85rem;
    }

    /* Metric value */
    div[data-testid="metric-container"] div {
        font-size: 1.25rem;
        font-weight: 600;
    }

    /* =========================
       PLOTLY CHART CONTAINER
    ==========================*/
    div[data-testid="stPlotlyChart"] {
        background: rgba(15, 20, 30, 0.85);
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 14px 38px rgba(0,0,0,0.6);
        transition: box-shadow 0.3s ease;
    }

    div[data-testid="stPlotlyChart"]:hover {
        box-shadow: 0 20px 55px rgba(0,0,0,0.8);
    }

    /* =========================
       CAPTION
    ==========================*/
    .stCaption {
        color: #9da7b3;
        text-align: center;
        margin-top: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <style>
    /* =================================================
       SMOOTH ENTRANCE ANIMATIONS
    ==================================================*/
    @keyframes fadeUp {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .stApp > div {
        animation: fadeUp 0.6s ease-out;
    }

    /* =================================================
       PRICE EMPHASIS (CURRENT PRICE)
    ==================================================*/
    .price-highlight {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        background: linear-gradient(90deg, #58a6ff, #7ee787);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: pulseGlow 2s infinite;
    }

    @keyframes pulseGlow {
        0% { text-shadow: 0 0 0 rgba(88,166,255,0.0); }
        50% { text-shadow: 0 0 18px rgba(88,166,255,0.45); }
        100% { text-shadow: 0 0 0 rgba(88,166,255,0.0); }
    }

    /* =================================================
       CONTEXT BADGES
    ==================================================*/
    .context-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.7rem;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        margin-right: 6px;
    }

    /* =================================================
       GLASS SEPARATORS
    ==================================================*/
    .glass-divider {
        height: 1px;
        background: linear-gradient(
            to right,
            rgba(255,255,255,0),
            rgba(255,255,255,0.2),
            rgba(255,255,255,0)
        );
        margin: 18px 0;
    }

    /* =================================================
       CHART FOCUS MODE
    ==================================================*/
    div[data-testid="stPlotlyChart"]:hover {
        outline: 2px solid rgba(88,166,255,0.35);
        outline-offset: -2px;
    }

    /* =================================================
       SCROLLBAR (DESKTOP)
    ==================================================*/
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05);
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(88,166,255,0.4);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(88,166,255,0.7);
    }

    /* =================================================
       SKELETON LOADING EFFECT
    ==================================================*/
    .skeleton {
        position: relative;
        overflow: hidden;
        background: rgba(255,255,255,0.08);
        border-radius: 12px;
    }

    .skeleton::after {
        content: "";
        position: absolute;
        top: 0;
        left: -150px;
        height: 100%;
        width: 150px;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255,255,255,0.25),
            transparent
        );
        animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
        100% {
            left: 100%;
        }
    }

    /* =================================================
       SUBTLE DEPTH ON HOVER FOLLOW
    ==================================================*/
    div[data-testid="metric-container"]:hover {
        transform: translateY(-6px) scale(1.01);
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
