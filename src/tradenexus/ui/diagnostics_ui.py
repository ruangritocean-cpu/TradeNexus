import streamlit as st
import pandas as pd
import json
import datetime
from tradenexus.diagnostics.health import check_system_health
from tradenexus.diagnostics.db_integrity import check_database_integrity
from tradenexus.diagnostics.data_quality import check_data_feed_quality
from tradenexus.diagnostics.alert_health import check_alert_configuration, simulate_dry_run_alert
from tradenexus.diagnostics.report import generate_release_readiness_report
from tradenexus.scanner.watchlist import load_watchlist

from tradenexus.data.cache import global_cache

def render_diagnostics_ui(db_path: str = None, watchlist_path: str = None):
    st.header("🧪 Diagnostics & Release Command Center")
    st.markdown("Diagnose environment configuration settings, database schemas, API connection paths, and dry run alerts.")
    
    # Cache Diagnostics Panel
    st.subheader("💾 Cache Diagnostics")
    diag = global_cache.get_diagnostics()
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Cached Items", diag["active_items"])
    with col_c2:
        st.metric("Cache Hits", diag["hits"])
    with col_c3:
        st.metric("Cache Misses", diag["misses"])
    with col_c4:
        st.metric("Hit Ratio", f"{diag['hit_ratio_pct']:.1f}%")
        
    if st.button("🧹 Clear Data Cache"):
        global_cache.clear()
        st.success("Data cache cleared successfully!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("⚙️ System Integrity Operations")
    
    # 1. Action controls
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    with col_a1:
        run_health = st.button("🔍 Run Health Check")
    with col_a2:
        run_integrity = st.button("🗄️ Check DB Integrity")
    with col_a3:
        run_feed = st.button("📡 Check Data Feed")
    with col_a4:
        run_report = st.button("📋 Generate Release Report")
        
    discord_url = st.session_state.get("line_token", "")
    tg_token = st.session_state.get("tg_token", "")
    tg_chat = st.session_state.get("tg_chat_id", "")
    
    # Renders results in panels
    if run_health:
        st.subheader("🏥 System Health Report")
        h = check_system_health(db_path, watchlist_path, discord_url, tg_token)
        st.markdown(f"**Health Status:** `{h['health_status']}`")
        st.json(h["checks"])
        if h["errors"]:
            st.error("Errors:\n" + "\n".join([f"- {e}" for e in h["errors"]]))
        if h["warnings"]:
            st.warning("Warnings:\n" + "\n".join([f"- {w}" for w in h["warnings"]]))
            
    if run_integrity:
        st.subheader("🗄️ Database Integrity Report")
        integ = check_database_integrity(db_path)
        st.markdown(f"**Integrity Status:** `{integ['integrity_status']}`")
        if integ["errors"]:
            st.error("Errors:\n" + "\n".join([f"- {e}" for e in integ["errors"]]))
        else:
            st.success("All required tables, indices, and schema constraints checked successfully!")
            
    if run_feed:
        st.subheader("📡 Data Feed Quality Report")
        watchlist = load_watchlist(watchlist_path)
        watchlist_symbols = [x["symbol"] for x in watchlist if x.get("enabled", True)][:3] # limit check to 3 to prevent slow load
        
        with st.spinner("Downloading price histories..."):
            feed = check_data_feed_quality(watchlist_symbols)
            st.markdown(f"**Data Feed status:** `{feed['feed_status']}`")
            st.write(feed["details"])
            
    if run_report or (not run_health and not run_integrity and not run_feed):
        st.subheader("📋 Release Readiness Report")
        watchlist = load_watchlist(watchlist_path)
        watchlist_symbols = [x["symbol"] for x in watchlist if x.get("enabled", True)][:2]
        
        rep = generate_release_readiness_report(
            db_path=db_path,
            watchlist_path=watchlist_path,
            discord_webhook=discord_url,
            tg_token=tg_token,
            symbols=watchlist_symbols
        )
        
        # Color coding metrics
        badge_colors = {
            "READY": ("rgba(52, 211, 153, 0.2)", "#34D399"),
            "WARNING": ("rgba(251, 191, 36, 0.2)", "#FBBF24"),
            "BLOCKED": ("rgba(248, 113, 113, 0.2)", "#F87171")
        }
        bg, txt = badge_colors.get(rep["release_status"], ("rgba(156, 163, 175, 0.2)", "#9CA3AF"))
        
        st.markdown(
            f"""
            <div style="background-color: {bg}; border: 1px solid {txt}; border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 1.1em; color: #E5E7EB;"><b>Release Readiness Status:</b></span>
                <span style="color: {txt}; font-size: 1.4em; font-weight: bold; margin-left: 10px;">{rep["release_status"]}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if rep["errors"]:
            st.error("❌ Critical Blockers:\n" + "\n".join([f"- {e}" for e in rep["errors"]]))
        else:
            st.success("✔ No critical release blockers found.")
            
        if rep["warnings"]:
            st.warning("⚠ Warnings:\n" + "\n".join([f"- {w}" for w in rep["warnings"]]))
            
    # 2. Alert Dry Run Simulator
    st.markdown("---")
    st.subheader("🔔 Alert Dry Run Simulator")
    
    with st.form("alert_dry_run_form"):
        col_dr1, col_dr2 = st.columns(2)
        with col_dr1:
            dr_ticker = st.text_input("Ticker Symbol", value="BTC-USD")
        with col_dr2:
            dr_tf = st.text_input("Timeframe", value="1h")
            
        dr_decision = st.selectbox("Decision State", options=["ENTRY TRIGGERED", "READY", "WATCH"])
        dr_dir = st.selectbox("Direction", options=["BUY", "SELL"])
        
        submit_dr = st.form_submit_button("Generate Dry Run Alert Payload")
        if submit_dr:
            strategy_mock = {
                "Decision": dr_decision,
                "Direction": dr_dir,
                "AlignmentType": "TREND_FOLLOWING",
                "Entry": 100.0,
                "StopLoss": 95.0,
                "TakeProfit1": 105.0,
                "TakeProfit2": 110.0,
                "RR_TP1": 2.0,
                "ConfluenceScore": 85.0,
                "Regime": "TRENDING_UP",
                "Reasons": ["1D trend bullish", "CDC Action Zone is Green"],
                "Warnings": []
            }
            
            payload_str = simulate_dry_run_alert(dr_ticker, dr_tf, strategy_mock)
            st.markdown("##### Rendered Message Payload:")
            st.code(payload_str, language="html")

    # 3. Provider Health Panel
    st.markdown("---")
    st.subheader("📡 Provider Health Dashboard")
    st.markdown("Monitor API latency, connection health, and fallback occurrences across all registered data providers.")
    
    from tradenexus.data.provider_health import load_all_providers_health
    health_data = load_all_providers_health()
    
    if not health_data:
        st.info("No provider health data recorded yet. Run a scan or test quality below to initialize.")
    else:
        for provider_name, stats in health_data.items():
            status_colors = {
                "OK": "rgba(52, 211, 153, 0.2)",
                "WARNING": "rgba(251, 191, 36, 0.2)",
                "FAILED": "rgba(248, 113, 113, 0.2)"
            }
            status_border = {
                "OK": "#34D399",
                "WARNING": "#FBBF24",
                "FAILED": "#F87171"
            }
            bg = status_colors.get(stats["health_status"], "rgba(156, 163, 175, 0.2)")
            border = status_border.get(stats["health_status"], "#9CA3AF")
            
            with st.container():
                st.markdown(
                    f"""
                    <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                        <span style="font-size: 1.2em; font-weight: bold; color: #E5E7EB;">Provider: {provider_name.upper()}</span>
                        <span style="float: right; font-weight: bold; color: {border};">{stats["health_status"]}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Success Calls", stats["success_count"])
                with col2:
                    st.metric("Failure Calls", stats["failure_count"])
                with col3:
                    st.metric("Avg Latency", f"{stats['average_fetch_duration']:.3f}s")
                with col4:
                    last_fail = stats["last_failure_at"]
                    st.markdown(f"**Last Failure:**<br><span style='font-size: 0.9em; color:#9CA3AF;'>{last_fail if last_fail else 'None'}</span>", unsafe_allow_html=True)
                    
    # 4. Data Quality Sandbox
    st.markdown("---")
    st.subheader("📊 Data Quality Analyzer (Sandbox)")
    st.markdown("Perform live data quality inspection for specific symbol/timeframe configurations.")
    
    with st.form("data_quality_sandbox_form"):
        col_dq1, col_dq2, col_dq3 = st.columns(3)
        with col_dq1:
            dq_symbol = st.text_input("Symbol", value="BTC-USD")
        with col_dq2:
            dq_interval = st.selectbox("Interval", options=["15m", "1h", "1d"])
        with col_dq3:
            dq_class = st.selectbox("Asset Class", options=["CRYPTO", "EQUITIES"])
            
        submit_dq = st.form_submit_button("Run Data Quality Diagnostic")
        if submit_dq:
            with st.spinner("Executing live diagnostics..."):
                from tradenexus.data.providers import fetch_ohlcv_result
                res = fetch_ohlcv_result(dq_symbol, dq_interval, asset_class=dq_class)
                
                status_color = {
                    "VALID": "#34D399",
                    "WARNING": "#FBBF24",
                    "INVALID": "#F87171"
                }
                color = status_color.get(res.data_quality_status, "#9CA3AF")
                
                st.markdown(
                    f"""
                    <div style="padding: 10px; border-left: 5px solid {color}; background-color: rgba(255,255,255,0.05); margin-bottom: 15px;">
                        <h4>Quality Status: <span style="color: {color};">{res.data_quality_status}</span></h4>
                        <p>Quality Score: <b>{res.quality_score}/100</b></p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Bars Fetched", res.bars_available)
                with col_m2:
                    st.metric("Provider Used", res.provider_used.upper())
                with col_m3:
                    st.metric("Fallback Activated", "Yes" if res.fallback_used else "No")
                    
                if res.latest_candle_time:
                    st.info(f"Latest Candle Time (UTC): {res.latest_candle_time}")
                    
                if res.errors:
                    st.error("Errors:\n" + "\n".join([f"- {e}" for e in res.errors]))
                if res.warnings:
                    st.warning("Warnings:\n" + "\n".join([f"- {w}" for w in res.warnings]))
                    
                if not res.df.empty:
                    st.dataframe(res.df.head())

