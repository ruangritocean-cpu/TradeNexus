import streamlit as st
import pandas as pd
from data_manager import fetch_ohlcv_data
from mtf_engine import resample_timeframe
from indicators import (
    calculate_cdc_actionzone,
    calculate_macd,
    calculate_smc_lite,
    calculate_mcdx_proxy,
    calculate_adaptive_trend,
    generate_trading_signal,
    calculate_bollinger_bands,
    calculate_adx
)
from ui_components import render_ttd_dashboard, draw_advanced_charts, render_trading_strategy_panel
from notifier import send_line_notify, send_telegram_message, format_signal_message

# Configure page settings
st.set_page_config(
    page_title="TradeNexus - Multi-Indicator Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for secure credentials and alert tracking
if "line_token" not in st.session_state:
    st.session_state["line_token"] = ""
if "tg_token" not in st.session_state:
    st.session_state["tg_token"] = ""
if "tg_chat_id" not in st.session_state:
    st.session_state["tg_chat_id"] = ""
if "last_alerted" not in st.session_state:
    st.session_state["last_alerted"] = {}

# Custom Styling for the header
st.markdown("""
    <style>
    .main-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-family: 'Inter', sans-serif;
        color: #9CA3AF;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">TradeNexus Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Advanced Multi-Timeframe Trading Strategy & Indicator Dashboard</p>', unsafe_allow_html=True)

# ----------------- SIDEBAR CONFIGURATION -----------------
st.sidebar.markdown("## 🔍 Market Explorer")

# Curated List of Assets
ASSET_LIST = {
    "₿ Bitcoin (BTC-USD)": "BTC-USD",
    "🪙 Gold Futures (GC=F)": "GC=F",
    "🥈 Silver Futures (SI=F)": "SI=F",
    "🇺🇸 Dow Jones (^DJI)": "^DJI",
    "🇺🇸 S&P 500 (^GSPC)": "^GSPC",
    "🇺🇸 Nasdaq Composite (^IXIC)": "^IXIC",
    "🇺🇸 Nasdaq 100 (^NDX)": "^NDX",
    "✍️ Custom Ticker...": "CUSTOM"
}

selected_asset = st.sidebar.selectbox(
    "Select Asset / เลือกสินทรัพย์",
    options=list(ASSET_LIST.keys()),
    index=0  # Defaults to Bitcoin
)

if ASSET_LIST[selected_asset] == "CUSTOM":
    ticker = st.sidebar.text_input(
        "Enter Custom Ticker / พิมพ์ชื่อย่อสินทรัพย์",
        value="AAPL",
        help="Enter a Yahoo Finance symbol (e.g. AAPL, EURUSD=X)"
    ).strip().upper()
else:
    ticker = ASSET_LIST[selected_asset]

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Indicator Parameters")

# Sidebar Collapsible Settings
with st.sidebar.expander("CDC ActionZone Settings"):
    cdc_fast = st.number_input("Fast EMA Length", min_value=5, max_value=50, value=12)
    cdc_slow = st.number_input("Slow EMA Length", min_value=10, max_value=100, value=26)

with st.sidebar.expander("MACD Settings"):
    macd_fast = st.number_input("MACD Fast Length", min_value=5, max_value=50, value=12)
    macd_slow = st.number_input("MACD Slow Length", min_value=10, max_value=100, value=26)
    macd_signal = st.number_input("MACD Signal Length", min_value=2, max_value=30, value=9)

with st.sidebar.expander("SMC Lite Settings"):
    smc_window = st.number_input("Swing Window Size", min_value=6, max_value=100, value=20, help="Lookback/lookforward window for swing points detection")

with st.sidebar.expander("MCDX Settings"):
    rsi_len = st.number_input("RSI Length", min_value=5, max_value=50, value=14)
    atr_len = st.number_input("ATR Length", min_value=5, max_value=50, value=14)

with st.sidebar.expander("🔔 Alert Settings"):
    line_token = st.text_input(
        "LINE Notify Token",
        value=st.session_state["line_token"],
        type="password",
        help="Enter your LINE Notify Bearer Token"
    )
    st.session_state["line_token"] = line_token
    
    tg_token = st.text_input(
        "Telegram Bot Token",
        value=st.session_state["tg_token"],
        type="password",
        help="Enter your Telegram Bot Token from BotFather"
    )
    st.session_state["tg_token"] = tg_token
    
    tg_chat_id = st.text_input(
        "Telegram Chat ID",
        value=st.session_state["tg_chat_id"],
        type="password",
        help="Enter your Telegram Chat ID"
    )
    st.session_state["tg_chat_id"] = tg_chat_id

st.sidebar.markdown("---")
# Warning message about API Limits
st.sidebar.info("""
**💡 Data Fetching Policy:**
To construct a complete Traders Trend Dashboard (TTD) from 15m up to 1D, we fetch the maximum available base timeframe (15m for 60 days) and resample it dynamically to higher timeframes (1h, 4h, 1d).
""")

# ----------------- CORE DATA PIPELINE -----------------
if not ticker:
    st.error("Please enter a valid Ticker Symbol.")
else:
    with st.spinner(f"Fetching market data for {ticker}..."):
        # Fetch base 15m data (maximum available 60 days)
        df_base = fetch_ohlcv_data(ticker, interval="15m")
        
    if df_base.empty:
        st.error(f"Failed to fetch data for ticker: `{ticker}`. Please check the symbol and try again.")
    else:
        # Calculate for each timeframe
        timeframes = ["15m", "1h", "4h", "1d"]
        tf_dfs = {}
        
        with st.spinner("Processing multiple timeframe engine & indicator calculations..."):
            # Resample and calculate indicators for each timeframe
            for tf in timeframes:
                if tf == "15m":
                    df_tf = df_base.copy()
                else:
                    df_tf = resample_timeframe(df_base, tf)
                
                # Apply indicators
                if not df_tf.empty:
                    df_tf = calculate_cdc_actionzone(df_tf, fast_len=cdc_fast, slow_len=cdc_slow)
                    df_tf = calculate_macd(df_tf, fast=macd_fast, slow=macd_slow, signal=macd_signal)
                    df_tf = calculate_smc_lite(df_tf, window=smc_window)
                    df_tf = calculate_mcdx_proxy(df_tf, rsi_len=rsi_len, atr_len=atr_len)
                    df_tf = calculate_adaptive_trend(df_tf)
                    df_tf = calculate_bollinger_bands(df_tf)
                    df_tf = calculate_adx(df_tf)
                    tf_dfs[tf] = df_tf
                else:
                    tf_dfs[tf] = pd.DataFrame()
                    
        # ----------------- UI VIEW: METRIC HEADER -----------------
        latest_15m = tf_dfs["15m"].iloc[-1] if not tf_dfs["15m"].empty else None
        prev_15m = tf_dfs["15m"].iloc[-2] if not tf_dfs["15m"].empty and len(tf_dfs["15m"]) > 1 else None
        
        if latest_15m is not None:
            price = latest_15m["Close"]
            prev_price = prev_15m["Close"] if prev_15m is not None else price
            price_change = price - prev_price
            price_change_pct = (price_change / prev_price) * 100 if prev_price > 0 else 0.0
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Latest Price", f"${price:,.2f}", f"{price_change_pct:+.2f}% (15m)")
            with c2:
                trend = latest_15m.get("CDC_Trend", "Neutral")
                trend_color = "🟢" if trend == "Bullish" else "🔴"
                st.metric("CDC Trend (15m)", f"{trend_color} {trend}")
            with c3:
                sm_val = latest_15m.get("MCDX_Smart", 0.0)
                st.metric("MCDX Smart Money", f"{sm_val:.1f}%", help="Percentage of institutional volume (Bankers)")
            with c4:
                sprt = latest_15m.get("Support_Level", 0.0)
                resis = latest_15m.get("Resistance_Level", 0.0)
                st.metric("SMC Support / Resistance", f"${sprt:,.2f} / ${resis:,.2f}")
                
        # ----------------- UI VIEW: TRADERS TREND DASHBOARD (TTD) -----------------
        st.subheader("📊 Traders Trend Dashboard (TTD)")
        
        # Prepare latest values for dashboard
        ttd_data = {}
        for tf in timeframes:
            if not tf_dfs[tf].empty:
                ttd_data[tf] = tf_dfs[tf].iloc[-1].to_dict()
            else:
                ttd_data[tf] = {}
                
        render_ttd_dashboard(ttd_data)
        
        st.markdown("---")
        
        # ----------------- UI VIEW: CHARTS & ANALYSIS -----------------
        st.subheader("📈 Technical Analysis Charts")
        
        # Timeframe Selector for the interactive chart
        selected_tf = st.selectbox("Select Chart Timeframe", options=timeframes, index=1, help="Choose which resampled timeframe data to display on the chart")
        
        df_to_plot = tf_dfs.get(selected_tf, pd.DataFrame())
        
        if df_to_plot.empty:
            st.error(f"No resampled data available for the `{selected_tf}` timeframe. Base timeframe has insufficient bars.")
        else:
            # Calculate trading strategy signals for the selected timeframe
            strategy = generate_trading_signal(df_to_plot.iloc[-1].to_dict())
            
            # Render actionable strategy panel
            render_trading_strategy_panel(strategy)
            
            # Auto-Alert Dispatcher with Candle-Level De-duplication
            last_candle_time = df_to_plot.index[-1]
            last_decision = strategy["Decision"]
            
            if last_decision != "NEUTRAL":
                key = (ticker, selected_tf)
                already_alerted = False
                if key in st.session_state["last_alerted"]:
                    prev_time, prev_decision = st.session_state["last_alerted"][key]
                    if prev_time == last_candle_time and prev_decision == last_decision:
                        already_alerted = True
                        
                if not already_alerted:
                    alert_msg = format_signal_message(ticker, selected_tf, strategy)
                    alert_sent = False
                    
                    if line_token:
                        success, info = send_line_notify(line_token, alert_msg)
                        if success:
                            st.sidebar.success(f"LINE Notify Auto-Sent for {ticker} ({selected_tf})")
                            alert_sent = True
                            
                    if tg_token and tg_chat_id:
                        success, info = send_telegram_message(tg_token, tg_chat_id, alert_msg)
                        if success:
                            st.sidebar.success(f"Telegram Auto-Sent for {ticker} ({selected_tf})")
                            alert_sent = True
                            
                    if alert_sent:
                        st.session_state["last_alerted"][key] = (last_candle_time, last_decision)
            
            # Manual trigger buttons
            st.markdown("### 🔔 Dispatch Signal Alerts")
            col_alert1, col_alert2 = st.columns([2, 5])
            with col_alert1:
                if st.button("Trigger Alert (Test) / ทดสอบส่งสัญญาณเตือน", help="Send the current trading signal via configured services"):
                    if not line_token and not (tg_token and tg_chat_id):
                        st.warning("Please configure LINE Notify or Telegram settings in the sidebar first.")
                    else:
                        alert_msg = format_signal_message(ticker, selected_tf, strategy)
                        
                        if line_token:
                            with st.spinner("Sending LINE Notify..."):
                                success, info = send_line_notify(line_token, alert_msg)
                                if success:
                                    st.success("LINE Notify sent successfully!")
                                else:
                                    st.error(f"LINE Notify failed: {info}")
                                    
                        if tg_token and tg_chat_id:
                            with st.spinner("Sending Telegram message..."):
                                success, info = send_telegram_message(tg_token, tg_chat_id, alert_msg)
                                if success:
                                    st.success("Telegram message sent successfully!")
                                else:
                                    st.error(f"Telegram failed: {info}")
            
            # Draw chart with strategy lines
            draw_advanced_charts(df_to_plot, ticker, selected_tf, strategy=strategy)
            
            # ----------------- UI VIEW: DATA EXPLORER -----------------
            with st.expander("📄 Data Explorer"):
                st.markdown(f"### Latest 10 Rows of Calculated Data ({selected_tf})")
                display_cols = ["Open", "High", "Low", "Close", "Volume", "EMA_Fast", "EMA_Slow", "CDC_Trend", "MACD", "MACD_Signal", "MACD_Hist", "Support_Level", "Resistance_Level", "MCDX_Proxy", "MCDX_Smart"]
                existing_cols = [c for c in display_cols if c in df_to_plot.columns]
                st.dataframe(df_to_plot[existing_cols].tail(10), use_container_width=True)
