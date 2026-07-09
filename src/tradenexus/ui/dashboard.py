import streamlit as st
import pandas as pd
import numpy as np
import datetime
import logging

# Data provider & resampling
from tradenexus.data.providers import fetch_ohlcv_data
from tradenexus.data.resampling import resample_timeframe

# Pipeline Unification
from tradenexus.pipeline.indicator_pipeline import calculate_all_indicators

# UI components
from tradenexus.signals.state import initialize_trade_state
from tradenexus.ui.technical_tab import render_technical_tab
from tradenexus.ui.strategy_lab_tab import render_strategy_lab_tab
from tradenexus.ui.watchlist_scanner_ui import render_watchlist_scanner_tab
from tradenexus.ui.portfolio_ui import render_portfolio_ui
from tradenexus.ui.diagnostics_ui import render_diagnostics_ui
from tradenexus.journal.db import init_db
from tradenexus.scanner.watchlist import load_watchlist

logger = logging.getLogger(__name__)

def run_dashboard():
    # Initialize SQLite Journal Database automatically
    init_db()

    # Initialize Streamlit session state for alerts and trades
    initialize_trade_state()
    if "line_token" not in st.session_state:
        st.session_state["line_token"] = ""
    if "tg_token" not in st.session_state:
        st.session_state["tg_token"] = ""
    if "tg_chat_id" not in st.session_state:
        st.session_state["tg_chat_id"] = ""

    # Custom Header Styling
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
    st.markdown('<p class="sub-title">Advanced Multi-Timeframe Trading Strategy & Decision Support System</p>', unsafe_allow_html=True)

    # ----------------- SIDEBAR PAGE NAVIGATION -----------------
    st.sidebar.markdown("## 🧭 Navigation / เมนูหลัก")
    page = st.sidebar.radio(
        "Select Page / เลือกหน้าจอ",
        ["📈 Technical Analysis", "🔬 Strategy Lab", "🔍 Watchlist Scanner", "🛡️ Portfolio Risk", "🧪 Diagnostics"]
    )

    st.sidebar.markdown("---")

    # ----------------- SIDEBAR CONFIGURATION (ONLY SHOWN FOR RELEVANT PAGES) -----------------
    ticker = ""
    tf_dfs = {}
    tf_warnings = {}

    if page in ["📈 Technical Analysis", "🔬 Strategy Lab"]:
        st.sidebar.markdown("## 🔍 Market Explorer")

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
            index=0
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

        with st.sidebar.expander("CDC ActionZone Settings"):
            cdc_fast = st.number_input("Fast EMA Length", min_value=5, max_value=50, value=12)
            cdc_slow = st.number_input("Slow EMA Length", min_value=10, max_value=100, value=26)

        with st.sidebar.expander("MACD Settings"):
            macd_fast = st.number_input("MACD Fast Length", min_value=5, max_value=50, value=12)
            macd_slow = st.number_input("MACD Slow Length", min_value=10, max_value=100, value=26)
            macd_signal = st.number_input("MACD Signal Length", min_value=2, max_value=30, value=9)

        with st.sidebar.expander("SMC Lite Settings"):
            smc_window = st.number_input("Swing Window Size", min_value=6, max_value=100, value=20)

        with st.sidebar.expander("MCDX Settings"):
            rsi_len = st.number_input("RSI Length", min_value=5, max_value=50, value=14)
            atr_len = st.number_input("ATR Length", min_value=5, max_value=50, value=14)

        with st.sidebar.expander("🔔 Alert Settings"):
            line_token = st.text_input(
                "Discord Webhook URL",
                value=st.session_state["line_token"],
                type="password",
                help="Enter your Discord Webhook URL for channel notifications"
            )
            st.session_state["line_token"] = line_token
            
            tg_token = st.text_input(
                "Telegram Bot Token",
                value=st.session_state["tg_token"],
                type="password",
                help="Enter your Telegram Bot Token"
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
        st.sidebar.info("""
        **💡 DSS Data Policy:**
        To avoid indicator warm-up bugs, yfinance data is downloaded natively per timeframe (15m, 1h, 1d) with extended history. 4H candles are resampled natively from the 1H data feed.
        """)

        # ----------------- DATA PRE-PROCESSING -----------------
        if not ticker:
            st.error("Please enter a valid Ticker Symbol.")
            return
            
        timeframes = ["15m", "1h", "4h", "1d"]
        
        with st.spinner(f"Downloading market data for {ticker}..."):
            df_15m, w_15m = fetch_ohlcv_data(ticker, interval="15m")
            df_1h, w_1h = fetch_ohlcv_data(ticker, interval="1h")
            df_1d, w_1d = fetch_ohlcv_data(ticker, interval="1d")
            
            tf_dfs["15m"] = df_15m
            tf_dfs["1h"] = df_1h
            tf_dfs["1d"] = df_1d
            
            tf_warnings["15m"] = w_15m
            tf_warnings["1h"] = w_1h
            tf_warnings["1d"] = w_1d
            
            # Resample 4H from native 1H data
            if not df_1h.empty:
                df_4h = resample_timeframe(df_1h, "4h")
                tf_dfs["4h"] = df_4h
                if len(df_4h) < 100:
                    tf_warnings["4h"] = f"Resampled 4H history is insufficient ({len(df_4h)} bars) for reliable indicator warmup."
                else:
                    tf_warnings["4h"] = ""
            else:
                tf_dfs["4h"] = pd.DataFrame()
                tf_warnings["4h"] = "Cannot construct 4H because 1H data is missing."

        # Process Indicators
        with st.spinner("Processing no-repaint SMC and technical indicators..."):
            for tf in timeframes:
                df_tf = tf_dfs[tf]
                if not df_tf.empty:
                    # Let the pipeline process all indicators
                    df_tf = calculate_all_indicators(df_tf)
                    # We can still customize the parameters locally if needed, but calculate_all_indicators is standard.
                    # To respect parameters from sliders:
                    from tradenexus.indicators.trend import calculate_cdc_actionzone, calculate_adaptive_trend
                    from tradenexus.indicators.momentum import calculate_macd, calculate_adx
                    from tradenexus.indicators.volatility import calculate_bollinger_bands
                    from tradenexus.indicators.smc import calculate_smc_lite
                    from tradenexus.indicators.mcdx import calculate_mcdx_proxy
                    from tradenexus.indicators.volume import calculate_volume_indicators
                    from tradenexus.indicators.structure import calculate_smc_structures
                    from tradenexus.indicators.liquidity import calculate_liquidity_zones
                    from tradenexus.regime.classifier import classify_market_regime
                    
                    df_tf = calculate_cdc_actionzone(df_tf, fast_len=cdc_fast, slow_len=cdc_slow)
                    df_tf = calculate_macd(df_tf, fast=macd_fast, slow=macd_slow, signal=macd_signal)
                    df_tf = calculate_smc_lite(df_tf, window=smc_window)
                    df_tf = calculate_mcdx_proxy(df_tf, rsi_len=rsi_len, atr_len=atr_len)
                    df_tf = calculate_adaptive_trend(df_tf)
                    df_tf = calculate_bollinger_bands(df_tf)
                    df_tf = calculate_adx(df_tf)
                    df_tf = calculate_volume_indicators(df_tf)
                    df_tf = calculate_smc_structures(df_tf)
                    df_tf = calculate_liquidity_zones(df_tf)
                    
                    # Rolling lookback regime classification - optimized for last 5 rows
                    primary_regimes = ["UNKNOWN"] * len(df_tf)
                    regime_scores = [0.0] * len(df_tf)
                    regime_flags_list = [""] * len(df_tf)
                    
                    start_idx = max(0, len(df_tf) - 5)
                    for idx in range(start_idx, len(df_tf)):
                        sub_df = df_tf.iloc[:idx+1]
                        reg_res = classify_market_regime(sub_df)
                        primary_regimes[idx] = reg_res["primary_regime"]
                        regime_scores[idx] = reg_res["regime_score"]
                        regime_flags_list[idx] = ",".join(reg_res["flags"])
                        
                    df_tf["primary_regime"] = primary_regimes
                    df_tf["regime_score"] = regime_scores
                    df_tf["regime_flags"] = regime_flags_list
                    
                    tf_dfs[tf] = df_tf

        # Display Data Quality Warnings if any
        warnings_to_show = [w for w in tf_warnings.values() if w]
        if warnings_to_show:
            for w in warnings_to_show:
                st.warning(f"⚠️ {w}")

    # ----------------- LAZY TABS RENDERING -----------------
    if page == "📈 Technical Analysis":
        render_technical_tab(ticker, tf_dfs, tf_warnings)
    elif page == "🔬 Strategy Lab":
        render_strategy_lab_tab(ticker, tf_dfs)
    elif page == "🔍 Watchlist Scanner":
        render_watchlist_scanner_tab()
    elif page == "🛡️ Portfolio Risk":
        render_portfolio_ui()
    elif page == "🧪 Diagnostics":
        render_diagnostics_ui()
