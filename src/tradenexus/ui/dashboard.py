import streamlit as st
import pandas as pd
import numpy as np
import datetime

# Data provider & resampling
from tradenexus.data.providers import fetch_ohlcv_data
from tradenexus.data.resampling import resample_timeframe

# Technical Indicators
from tradenexus.indicators.trend import calculate_cdc_actionzone, calculate_adaptive_trend
from tradenexus.indicators.momentum import calculate_macd, calculate_adx
from tradenexus.indicators.volatility import calculate_bollinger_bands
from tradenexus.indicators.smc import calculate_smc_lite
from indicators import calculate_mcdx_proxy  # Keep existing proxy logic

# Decision Engine & Alerts
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk
from tradenexus.indicators.volume import calculate_volume_indicators
from tradenexus.indicators.structure import calculate_smc_structures
from tradenexus.indicators.liquidity import calculate_liquidity_zones
from tradenexus.regime.classifier import classify_market_regime
from tradenexus.signals.state import (
    initialize_trade_state, 
    start_trade, 
    update_trade_status, 
    get_active_trade, 
    is_trade_active,
    clear_active_trade
)
from tradenexus.alerts.telegram import send_telegram_message
from tradenexus.alerts.discord import send_discord_webhook

# Sprint 3 additions
from tradenexus.journal.db import init_db
from tradenexus.journal.models import Signal
from tradenexus.journal.repository import (
    insert_signal, 
    load_signals, 
    generate_signal_id, 
    load_alert_logs, 
    update_signal_outcome,
    load_signals_paginated,
    load_alerts_paginated,
    export_signals_to_csv,
    export_alert_log_to_csv,
    export_trades_to_csv,
    clear_backtest_results,
    clear_demo_trades,
    clear_all_journal_data
)
from tradenexus.journal.outcome import evaluate_signal_outcome
from tradenexus.journal.guard import is_candle_closed
from tradenexus.alerts.dispatcher import dispatch_alert
from tradenexus.backtest.engine import run_mtf_backtest
from tradenexus.backtest.metrics import calculate_backtest_metrics

# UI components
from tradenexus.ui.components import (
    render_ttd_dashboard, 
    render_trading_strategy_panel, 
    render_top_metrics_bar,
    render_backtest_metrics_panel,
    render_breakdown_tables
)
from tradenexus.ui.charts import draw_advanced_charts
from tradenexus.ui.watchlist_scanner_ui import render_watchlist_scanner_tab
from tradenexus.ui.portfolio_ui import render_portfolio_ui
from tradenexus.ui.diagnostics_ui import render_diagnostics_ui
from notifier import format_signal_message  # Keep formatting logic

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

    # ----------------- SIDEBAR CONFIGURATION -----------------
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

    # ----------------- CORE DATA PIPELINE -----------------
    if not ticker:
        st.error("Please enter a valid Ticker Symbol.")
    else:
        tf_warnings = {}
        tf_dfs = {}
        
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
                    
                    # Rolling look-back regime classification - optimized for last 5 rows
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

        # ----------------- UI TABS -----------------
        tab_charts, tab_lab, tab_scanner, tab_portfolio, tab_diagnostics = st.tabs(["📈 Technical Analysis Charts", "📊 Strategy Lab", "📡 Watchlist Scanner", "🛡️ Portfolio Risk", "🧪 Diagnostics"])
        
        with tab_charts:
            # ----------------- UI VIEW: METRIC HEADER -----------------
            latest_15m = tf_dfs["15m"].iloc[-1] if not tf_dfs["15m"].empty else None
            prev_15m = tf_dfs["15m"].iloc[-2] if not tf_dfs["15m"].empty and len(tf_dfs["15m"]) > 1 else None
            
            if latest_15m is not None:
                price = latest_15m["Close"]
                prev_price = prev_15m["Close"] if prev_15m is not None else price
                price_change = price - prev_price
                price_change_pct = (price_change / prev_price) * 100 if prev_price > 0 else 0.0
                
                render_top_metrics_bar(
                    price=price,
                    price_change_pct=price_change_pct,
                    trend=latest_15m.get("CDC_Trend", "Neutral"),
                    sm_val=latest_15m.get("MCDX_Smart", 0.0),
                    support=latest_15m.get("Support_Level", 0.0),
                    resistance=latest_15m.get("Resistance_Level", 0.0)
                )

            # ----------------- UI VIEW: CONFLUENCE MATRIX -----------------
            st.subheader("📊 Confluence Matrix")
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
            selected_tf = st.selectbox("Select Chart Timeframe", options=timeframes, index=1)
            
            df_to_plot = tf_dfs.get(selected_tf, pd.DataFrame())
            
            if df_to_plot.empty:
                st.error(f"No resampled data available for the `{selected_tf}` timeframe.")
            else:
                latest_row = df_to_plot.iloc[-1]
                latest_row_dict = latest_row.to_dict()
                
                # 1. Multi-Timeframe Hierarchy alignment
                bias_1d = tf_dfs["1d"].iloc[-1].get("CDC_Trend", "Neutral") if not tf_dfs["1d"].empty else "Neutral"
                setup_4h = tf_dfs["4h"].iloc[-1].get("CDC_Trend", "Neutral") if not tf_dfs["4h"].empty else "Neutral"
                trigger_1h = tf_dfs["1h"].iloc[-1].get("CDC_Trend", "Neutral") if not tf_dfs["1h"].empty else "Neutral"
                exec_15m = tf_dfs["15m"].iloc[-1].get("CDC_Trend", "Neutral") if not tf_dfs["15m"].empty else "Neutral"
                
                mtf_result = evaluate_mtf_hierarchy(bias_1d, setup_4h, trigger_1h, exec_15m)
                alignment_type = mtf_result["alignment_type"]
                
                # 2. Risk Target calculation & veto logic
                support_val = latest_row.get("Support_Level", 0.0)
                resistance_val = latest_row.get("Resistance_Level", 0.0)
                atr_val = latest_row.get("ATR", 0.0)
                
                # Calculate directional score to map trade direction
                scoring_result = calculate_confluence_score(latest_row_dict)
                dir_score = scoring_result["directional_score"]
                
                base_dec = "NEUTRAL"
                if dir_score >= 60:
                    base_dec = "BUY"
                elif dir_score <= -60:
                    base_dec = "SELL"
                    
                risk_result = validate_trade_risk(
                    price=latest_row["Close"],
                    decision=base_dec,
                    support=support_val,
                    resistance=resistance_val,
                    atr=atr_val,
                    rr_min=1.5
                )
                
                # Inject calculated RR back into scoring to update quality score
                latest_row_dict["RR_TP1"] = risk_result["RR_TP1"]
                scoring_result = calculate_confluence_score(latest_row_dict)
                
                # 3. Decision State Machine
                is_warmup_insufficient = (tf_warnings.get(selected_tf, "") != "")
                
                # Default State
                decision_state = "NO TRADE"
                
                if is_trade_active():
                    decision_state = "MANAGE TRADE"
                elif is_warmup_insufficient:
                    decision_state = "NO TRADE"
                elif risk_result["Vetoed"]:
                    decision_state = "NO TRADE"
                elif base_dec == "NEUTRAL":
                    decision_state = "WATCH"
                else: # BUY/SELL
                    if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
                        if scoring_result["confluence_score"] >= 70:
                            decision_state = "ENTRY TRIGGERED"
                        else:
                            decision_state = "READY"
                    else:
                        decision_state = "WATCH"

                # Apply Regime-Aware overrides
                regime = latest_row.get("primary_regime", "UNKNOWN")
                flags = latest_row.get("regime_flags", "").split(",") if latest_row.get("regime_flags", "") else []
                
                decision_state, regime_reasons, regime_warnings = apply_regime_decision_rules(
                    decision_state=decision_state,
                    primary_regime=regime,
                    flags=flags,
                    confluence_score=scoring_result["confluence_score"]
                )

                strategy = {
                    "Decision": decision_state,
                    "Direction": base_dec,
                    "AlignmentType": alignment_type,
                    "ConfluenceScore": scoring_result["confluence_score"],
                    "DirectionalScore": dir_score,
                    "QualityScore": scoring_result["quality_score"],
                    "Entry": risk_result["Entry"],
                    "StopLoss": risk_result["StopLoss"],
                    "TakeProfit1": risk_result["TakeProfit1"],
                    "TakeProfit2": risk_result["TakeProfit2"],
                    "RR_TP1": risk_result["RR_TP1"],
                    "RR_TP2": risk_result["RR_TP2"],
                    "Reasons": scoring_result["reasons"] + mtf_result["reasons"] + regime_reasons,
                    "Warnings": scoring_result["warnings"] + mtf_result["warnings"] + regime_warnings,
                    "Vetoed": risk_result["Vetoed"],
                    "VetoReason": risk_result["VetoReason"],
                    "DataQualityWarning": is_warmup_insufficient,
                    "Regime": regime,
                    "RegimeScore": latest_row.get("regime_score", 0.0),
                    "RegimeFlags": latest_row.get("regime_flags", ""),
                    "VolumeConfirmation": latest_row.get("Volume_Confirmation", "NEUTRAL"),
                    "VwapAlignment": "BULLISH" if latest_row["Close"] > latest_row.get("VWAP", latest_row["Close"]) else "BEARISH",
                    "BOS": latest_row.get("BOS_Present", 0),
                    "CHOCH": latest_row.get("CHOCH_Present", 0),
                    "FVG": latest_row.get("FVG_Present", 0),
                    "LiquiditySweep": latest_row.get("Liquidity_Sweep", 0)
                }
                
                # Render upgraded premium Decision Card
                render_trading_strategy_panel(strategy)
                
                # Render deterministic Decision Brief explanation panel
                from tradenexus.explain.decision_brief import generate_decision_brief
                from tradenexus.explain.templates import format_full_brief
                
                brief_data = {
                    "symbol": ticker,
                    "timeframe": selected_tf,
                    "decision_state": decision_state,
                    "direction": base_dec,
                    "alignment_type": alignment_type,
                    "confluence_score": strategy["ConfluenceScore"],
                    "primary_regime": regime,
                    "regime_flags": flags,
                    "entry": strategy["Entry"],
                    "sl": strategy["StopLoss"],
                    "tp1": strategy["TakeProfit1"],
                    "tp2": strategy["TakeProfit2"],
                    "rr_tp1": strategy["RR_TP1"],
                    "warnings": strategy["Warnings"],
                    "support_level": support_val,
                    "resistance_level": resistance_val
                }
                
                try:
                    brief = generate_decision_brief(brief_data)
                    with st.expander("📖 Read Decision Explanation Brief", expanded=True):
                        st.markdown(format_full_brief(brief))
                except Exception as brief_err:
                    st.warning(f"⚠️ ไม่สามารถสร้างสรุปการวิเคราะห์สอดคล้องได้ในขณะนี้เนื่องจากระบบฐานข้อมูลกำลังอัปเดต (ข้อผิดพลาด: {str(brief_err)})")
                    logger.error(f"Failed to generate decision brief: {str(brief_err)}")
                
                # ----------------- ACTIVE POSITION UI CONTROLS -----------------
                if decision_state == "MANAGE TRADE":
                    active_trade = get_active_trade()
                    st.info(f"🛡️ **Active Position Info:** {active_trade['direction']} {active_trade['symbol']} entered at ${active_trade['entry']:,.2f} on {active_trade['entry_time']}.")
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        if st.button("Simulate TP1 Hit"):
                            update_trade_status("TP1_HIT")
                            st.rerun()
                    with col_m2:
                        if st.button("Close Active Position"):
                            update_trade_status("CLOSED")
                            st.rerun()
                elif decision_state == "ENTRY TRIGGERED":
                    if st.button("Confirm & Open Position (Simulation)"):
                        start_trade(
                            symbol=ticker,
                            direction=base_dec,
                            entry=risk_result["Entry"],
                            sl=risk_result["StopLoss"],
                            tp1=risk_result["TakeProfit1"],
                            tp2=risk_result["TakeProfit2"]
                        )
                        st.success(f"Position opened for {ticker}!")
                        st.rerun()

                # ----------------- CLOSED CANDLE AUTO ALERTS & JOURNAL -----------------
                # Alert only on fully CLOSED candle (index -2) to prevent look-ahead & repaints!
                if len(df_to_plot) > 2:
                    closed_row = df_to_plot.iloc[-2]
                    closed_row_dict = closed_row.to_dict()
                    closed_time = df_to_plot.index[-2]
                    
                    # Verify using closed candle guard
                    if is_candle_closed(closed_time, selected_tf, mode="live"):
                        # Check alignment & scoring on closed row
                        c_scoring = calculate_confluence_score(closed_row_dict)
                        c_dir = c_scoring["directional_score"]
                        
                        c_dec = "NEUTRAL"
                        if c_dir >= 60:
                            c_dec = "BUY"
                        elif c_dir <= -60:
                            c_dec = "SELL"
                            
                        c_risk = validate_trade_risk(
                            price=closed_row["Close"],
                            decision=c_dec,
                            support=closed_row.get("Support_Level", 0.0),
                            resistance=closed_row.get("Resistance_Level", 0.0),
                            atr=closed_row.get("ATR", 0.0),
                            rr_min=1.5
                        )
                        
                        # Update closed row dictionary with calculated RR
                        closed_row_dict["RR_TP1"] = c_risk["RR_TP1"]
                        c_scoring = calculate_confluence_score(closed_row_dict)
                        
                        # Map closed state
                        c_state = "NO TRADE"
                        if is_warmup_insufficient or c_risk["Vetoed"]:
                            c_state = "NO TRADE"
                        elif c_dec == "NEUTRAL":
                            c_state = "WATCH"
                        else:
                            if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
                                if c_scoring["confluence_score"] >= 70:
                                    c_state = "ENTRY TRIGGERED"
                                else:
                                    c_state = "READY"
                            else:
                                c_state = "WATCH"
                                
                        # Apply Regime-Aware overrides on closed candle signal
                        c_regime = closed_row.get("primary_regime", "UNKNOWN")
                        c_flags = closed_row.get("regime_flags", "").split(",") if closed_row.get("regime_flags", "") else []
                        c_state, c_regime_reasons, c_regime_warnings = apply_regime_decision_rules(
                            decision_state=c_state,
                            primary_regime=c_regime,
                            flags=c_flags,
                            confluence_score=c_scoring["confluence_score"]
                        )
                        
                        # Process Closed Signal insertion
                        # Check if closed signal is actionable (READY, ENTRY TRIGGERED)
                        is_act = 1 if c_state in ["READY", "ENTRY TRIGGERED"] else 0
                        
                        sig_id = generate_signal_id(
                            symbol=ticker,
                            timeframe=selected_tf,
                            candle_close_time=closed_time.isoformat(),
                            decision_state=c_state,
                            direction=c_dec,
                            entry=c_risk["Entry"],
                            sl=c_risk["StopLoss"],
                            tp1=c_risk["TakeProfit1"]
                        )
                        
                        # Construct signal dataclass
                        closed_signal = Signal(
                            signal_id=sig_id,
                            symbol=ticker,
                            timeframe=selected_tf,
                            candle_close_time=closed_time.isoformat(),
                            decision_state=c_state,
                            direction=c_dec,
                            alignment_type=alignment_type,
                            entry=c_risk["Entry"],
                            sl=c_risk["StopLoss"],
                            tp1=c_risk["TakeProfit1"],
                            tp2=c_risk["TakeProfit2"],
                            rr_tp1=c_risk["RR_TP1"],
                            rr_tp2=c_risk["RR_TP2"],
                            confluence_score=c_scoring["confluence_score"],
                            directional_score=c_dir,
                            quality_score=c_scoring["quality_score"],
                            market_bias=bias_1d,
                            setup_direction=setup_4h,
                            trigger_direction=trigger_1h,
                            execution_direction=exec_15m,
                            smc_support_source=closed_row.get("Support_Source", "FALLBACK"),
                            smc_resistance_source=closed_row.get("Resistance_Source", "FALLBACK"),
                            data_quality_valid=0 if is_warmup_insufficient else 1,
                            is_actionable=is_act,
                            reasons=c_scoring["reasons"] + mtf_result["reasons"] + c_regime_reasons,
                            warnings=c_scoring["warnings"] + mtf_result["warnings"] + c_regime_warnings,
                            primary_regime=c_regime,
                            regime_score=closed_row.get("regime_score", 0.0),
                            regime_flags=closed_row.get("regime_flags", ""),
                            volume_confirmation=closed_row.get("Volume_Confirmation", "NEUTRAL"),
                            vwap_alignment="BULLISH" if closed_row["Close"] > closed_row.get("VWAP", closed_row["Close"]) else "BEARISH",
                            bos_present=closed_row.get("BOS_Present", 0),
                            choch_present=closed_row.get("CHOCH_Present", 0),
                            fvg_present=closed_row.get("FVG_Present", 0),
                            liquidity_sweep_present=closed_row.get("Liquidity_Sweep", 0)
                        )
                        
                        # Save to database
                        insert_signal(closed_signal)
                        
                        # Update outcome of previously OPEN signals for the same ticker
                        open_signals = [s for s in load_signals() if s.outcome_status == "OPEN" and s.symbol == ticker and s.timeframe == selected_tf]
                        for op_sig in open_signals:
                            op_entry_time = pd.Timestamp(op_sig.candle_close_time)
                            out_eval = evaluate_signal_outcome(
                                df=df_to_plot,
                                entry_time=op_entry_time,
                                direction=op_sig.direction,
                                entry=op_sig.entry,
                                sl=op_sig.sl,
                                tp1=op_sig.tp1,
                                tp2=op_sig.tp2,
                                max_bars=100
                            )
                            if out_eval["status"] != "OPEN":
                                update_signal_outcome(
                                    signal_id=op_sig.signal_id,
                                    outcome_status=out_eval["status"],
                                    outcome_time=out_eval["outcome_time"],
                                    bars_to_outcome=out_eval["bars_to_outcome"],
                                    realized_r=out_eval["realized_r_multiple"]
                                )
                        
                        # Alert dispatch logic
                        if c_state == "ENTRY TRIGGERED":
                            closed_strategy = {
                                "Decision": c_state,
                                "Direction": c_dec,
                                "AlignmentType": alignment_type,
                                "Entry": c_risk["Entry"],
                                "StopLoss": c_risk["StopLoss"],
                                "TakeProfit1": c_risk["TakeProfit1"],
                                "TakeProfit2": c_risk["TakeProfit2"],
                                "RR_TP1": c_risk["RR_TP1"],
                                "ConfluenceScore": c_scoring["confluence_score"],
                                "Reasons": closed_signal.reasons,
                                "Warnings": closed_signal.warnings
                            }
                            
                            # Dispatch alerts (safely avoids duplicate sending internally)
                            dispatch_alert(
                                signal_id=sig_id,
                                ticker=ticker,
                                timeframe=selected_tf,
                                strategy=closed_strategy,
                                discord_webhook_url=line_token,
                                tg_bot_token=tg_token,
                                tg_chat_id=tg_chat_id
                            )

                # Manual Alert Trigger Button (uses CURRENT active candle for instant testing)
                st.markdown("### 🔔 Dispatch Signal Alerts")
                col_alert1, col_alert2 = st.columns([2, 5])
                with col_alert1:
                    if st.button("Trigger Alert (Test) / ทดสอบส่งสัญญาณเตือน"):
                        if not line_token and not (tg_token and tg_chat_id):
                            st.warning("Please configure Discord Webhook or Telegram settings in the sidebar first.")
                        else:
                            legacy_strategy_payload = {
                                "Decision": decision_state,
                                "Direction": base_dec,
                                "AlignmentType": alignment_type,
                                "Entry": risk_result["Entry"],
                                "StopLoss": risk_result["StopLoss"],
                                "TakeProfit1": risk_result["TakeProfit1"],
                                "TakeProfit2": risk_result["TakeProfit2"],
                                "RR_TP1": risk_result["RR_TP1"],
                                "ConfluenceScore": scoring_result["confluence_score"],
                                "Reasons": strategy["Reasons"],
                                "Warnings": strategy["Warnings"]
                            }
                            # Send direct test webhook alert bypassing deduplication checking
                            dispatch_alert(
                                signal_id=f"test_manual_{int(datetime.datetime.now().timestamp())}",
                                ticker=ticker,
                                timeframe=selected_tf,
                                strategy=legacy_strategy_payload,
                                discord_webhook_url=line_token,
                                tg_bot_token=tg_token,
                                tg_chat_id=tg_chat_id
                            )
                            st.success("Test alert sent manually!")

                # Plot main Plotly charts
                legacy_strategy_draw = {
                    "Decision": decision_state,
                    "Entry": risk_result["Entry"],
                    "StopLoss": risk_result["StopLoss"],
                    "TakeProfit1": risk_result["TakeProfit1"],
                    "TakeProfit2": risk_result["TakeProfit2"]
                }
                
                with st.expander("🔍 Chart Overlay Options / ตัวเลือกการซ้อนทับบนกราฟ"):
                    col_ch1, col_ch2, col_ch3 = st.columns(3)
                    with col_ch1:
                        show_vwap = st.checkbox("Show VWAP / แสดง VWAP", value=False)
                        show_fvg = st.checkbox("Show FVG / แสดง FVG (Fair Value Gap)", value=False)
                    with col_ch2:
                        show_ob = st.checkbox("Show Order Blocks / แสดง Order Blocks", value=False)
                        show_sweeps = st.checkbox("Show Liquidity Sweeps / แสดง Liquidity Sweeps", value=False)
                    with col_ch3:
                        show_bos_choch = st.checkbox("Show BOS & CHOCH / แสดง BOS & CHOCH", value=False)
                        show_eql_eqh = st.checkbox("Show Equal Highs/Lows / แสดง Equal Highs/Lows", value=False)
                        
                draw_advanced_charts(
                    df_to_plot, 
                    ticker, 
                    selected_tf, 
                    strategy=legacy_strategy_draw,
                    show_vwap=show_vwap,
                    show_fvg=show_fvg,
                    show_ob=show_ob,
                    show_sweeps=show_sweeps,
                    show_bos_choch=show_bos_choch,
                    show_eql_eqh=show_eql_eqh
                )
                
                # Data Explorer expander
                with st.expander("📄 Data Explorer"):
                    st.markdown(f"### Latest 10 Rows of Calculated Data ({selected_tf})")
                    display_cols = ["Open", "High", "Low", "Close", "Volume", "EMA_Fast", "EMA_Slow", "Support_Level", "Resistance_Level", "MCDX_Proxy", "MCDX_Smart", "Support_Source", "Resistance_Source"]
                    existing_cols = [c for c in display_cols if c in df_to_plot.columns]
                    st.dataframe(df_to_plot[existing_cols].tail(10), use_container_width=True)

        with tab_lab:
            st.header("📊 Strategy Lab")
            st.markdown("Analyze signal histories, check alert logs, and run backtests using non-repainting historical setups.")
            
            # Sub-tab structure
            tab_journal, tab_backtest = st.tabs(["📑 Signal Journal", "⚙️ Historical Backtest"])
            
            with tab_journal:
                st.subheader("Signal Journal Summary")
                summary_sigs = load_signals()
                act_sigs = [s for s in summary_sigs if s.is_actionable == 1]
                
                # Convert list to dict list for calculations
                trades_dict_list = []
                for s in act_sigs:
                    trades_dict_list.append({
                        "status": s.outcome_status,
                        "realized_r_multiple": s.realized_r_multiple,
                        "bars_to_outcome": s.bars_to_outcome if s.bars_to_outcome else 0
                    })
                    
                journal_metrics = calculate_backtest_metrics(trades_dict_list)
                
                col_j1, col_j2, col_j3, col_j4 = st.columns(4)
                with col_j1:
                    st.metric("Total Actionable Signals", len(act_sigs))
                with col_j2:
                    st.metric("Win Rate", f"{journal_metrics['win_rate']:.1f}%")
                with col_j3:
                    st.metric("Avg R multiple", f"{journal_metrics['expectancy']:+.2f} R")
                with col_j4:
                    st.metric("All Signals (incl. watch/no-trade)", len(summary_sigs))
                    
                st.markdown("---")
                st.subheader("Latest Recorded Signals")
                
                # Paginated signals loading
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    sig_limit = st.selectbox("Signals per page", [10, 20, 50, 100], index=1)
                with col_p2:
                    if "sig_page" not in st.session_state:
                        st.session_state.sig_page = 0
                    col_page_prev, col_page_next = st.columns(2)
                    with col_page_prev:
                        if st.button("⬅️ Previous Page") and st.session_state.sig_page > 0:
                            st.session_state.sig_page -= 1
                            st.rerun()
                    with col_page_next:
                        if st.button("Next Page ➡️"):
                            st.session_state.sig_page += 1
                            st.rerun()
                            
                offset = st.session_state.sig_page * sig_limit
                all_sigs = load_signals_paginated(limit=sig_limit, offset=offset)
                
                if all_sigs:
                    df_sigs = pd.DataFrame([{
                        "Time": s.candle_close_time,
                        "Symbol": s.symbol,
                        "Timeframe": s.timeframe,
                        "Decision": s.decision_state,
                        "Direction": s.direction,
                        "Alignment": s.alignment_type,
                        "Entry": s.entry,
                        "SL": s.sl,
                        "TP1": s.tp1,
                        "Confluence": f"{s.confluence_score:.1f}%",
                        "Outcome": s.outcome_status,
                        "R realized": f"{s.realized_r_multiple:+.2f}R"
                    } for s in all_sigs])
                    st.dataframe(df_sigs, use_container_width=True)
                    st.caption(f"Showing page {st.session_state.sig_page + 1}")
                else:
                    st.info("No signals recorded on this page.")
                    
                st.markdown("---")
                st.subheader("Alert Log History")
                
                # Paginated alerts loading
                col_ap1, col_ap2 = st.columns(2)
                with col_ap1:
                    alert_limit = st.selectbox("Alerts per page", [10, 20, 50, 100], index=1)
                with col_ap2:
                    if "alert_page" not in st.session_state:
                        st.session_state.alert_page = 0
                    col_apage_prev, col_apage_next = st.columns(2)
                    with col_apage_prev:
                        if st.button("⬅️ Prev Page (Alerts)") and st.session_state.alert_page > 0:
                            st.session_state.alert_page -= 1
                            st.rerun()
                    with col_apage_next:
                        if st.button("Next Page (Alerts) ➡️"):
                            st.session_state.alert_page += 1
                            st.rerun()
                            
                alert_offset = st.session_state.alert_page * alert_limit
                alert_logs = load_alerts_paginated(limit=alert_limit, offset=alert_offset)
                
                if alert_logs:
                    df_alerts = pd.DataFrame([{
                        "Time": a.sent_at,
                        "Signal ID": a.signal_id[:12] + "...",
                        "Provider": a.provider,
                        "Status": a.status,
                        "Error": a.error_message if a.error_message else "-"
                    } for a in alert_logs])
                    st.dataframe(df_alerts, use_container_width=True)
                    st.caption(f"Showing page {st.session_state.alert_page + 1}")
                else:
                    st.info("No alert records logged on this page.")
                    
                st.markdown("---")
                st.subheader("📤 Export Data & Clears")
                
                col_ex1, col_ex2, col_ex3 = st.columns(3)
                with col_ex1:
                    sig_csv = export_signals_to_csv()
                    st.download_button("📥 Download Signals CSV", sig_csv, "signals.csv", "text/csv")
                with col_ex2:
                    alert_csv = export_alert_log_to_csv()
                    st.download_button("📥 Download Alerts CSV", alert_csv, "alerts.csv", "text/csv")
                with col_ex3:
                    trade_csv = export_trades_to_csv()
                    st.download_button("📥 Download Trades CSV", trade_csv, "trades.csv", "text/csv")
                    
                st.markdown("### 🧹 Safe Clears")
                col_cl1, col_cl2, col_cl3 = st.columns(3)
                with col_cl1:
                    if st.button("🗑️ Clear Backtests Only", help="Erases only historical backtest runs"):
                        clear_backtest_results()
                        st.success("Backtest results cleared!")
                        st.rerun()
                with col_cl2:
                    if st.button("🗑️ Clear Demo Trades Only", help="Clears only active/simulated demo trade logs"):
                        clear_demo_trades()
                        st.success("Demo trades cleared!")
                        st.rerun()
                with col_cl3:
                    if st.button("🗑️ Clear All Journal Data", help="DANGER: Resets the entire signal database"):
                        clear_all_journal_data()
                        st.success("Entire database reset successfully!")
                        st.rerun()
                    
            with tab_backtest:
                st.subheader("Run Historical Backtest")
                
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    b_tf = st.selectbox("Backtest Trigger Timeframe", options=["15m", "1h", "4h"], index=1)
                with col_b2:
                    b_rr = st.number_input("Min Risk/Reward (TP1 Target)", min_value=1.0, max_value=5.0, value=1.5, step=0.1)
                with col_b3:
                    b_hold = st.number_input("Max Bars to Hold Position", min_value=10, max_value=500, value=100, step=10)
                    
                col_bc1, col_bc2 = st.columns(2)
                with col_bc1:
                    b_slippage = st.number_input("Slippage (Points)", min_value=0.0, value=0.0, step=0.01)
                with col_bc2:
                    b_commission = st.number_input("Commission (Pct %)", min_value=0.0, max_value=1.0, value=0.0, step=0.01)
                    
                if st.button("🚀 Run Backtest"):
                    with st.spinner("Processing sequential chronological backtest..."):
                        backtest_res = run_mtf_backtest(
                            tf_dfs=tf_dfs,
                            symbol=ticker,
                            trigger_tf=b_tf,
                            rr_threshold=b_rr,
                            max_bars_to_hold=b_hold,
                            slippage_points=b_slippage,
                            commission_pct=b_commission
                        )
                        
                        b_signals = backtest_res["signals"]
                        
                        if not b_signals:
                            st.warning("No entry signals triggered during the backtest timeframe. Try extending the yfinance data history or lowering indicator settings.")
                        else:
                            st.success(f"Backtest completed! Evaluated {len(b_signals)} triggered signals.")
                            
                            # Calculate metrics
                            trades_list = []
                            for s in b_signals:
                                trades_list.append({
                                    "status": s["outcome_status"],
                                    "realized_r_multiple": s["realized_r_multiple"],
                                    "bars_to_outcome": s["bars_to_outcome"]
                                })
                                
                            metrics = calculate_backtest_metrics(trades_list)
                            
                            # Render UI panels
                            render_backtest_metrics_panel(metrics)
                            
                            st.markdown("---")
                            render_breakdown_tables(b_signals)
                            
                            st.markdown("---")
                            st.subheader("Detail Backtest Signals")
                            df_bt_details = pd.DataFrame([{
                                "Time": s["candle_close_time"],
                                "Direction": s["direction"],
                                "Alignment": s["alignment_type"],
                                "Entry": s["entry"],
                                "SL": s["sl"],
                                "TP1": s["tp1"],
                                "TP2": s["tp2"],
                                "Confluence": f"{s['confluence_score']:.1f}%",
                                "Outcome": s["outcome_status"],
                                "R Realized": f"{s['realized_r_multiple']:+.2f}R",
                                "Bars": s["bars_to_outcome"]
                            } for s in b_signals])
                            st.dataframe(df_bt_details, use_container_width=True)
                            
        with tab_scanner:
            render_watchlist_scanner_tab()
            
        with tab_portfolio:
            render_portfolio_ui()
            
        with tab_diagnostics:
            render_diagnostics_ui()
