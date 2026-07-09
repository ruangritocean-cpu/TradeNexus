import streamlit as st
import pandas as pd
import numpy as np
import logging

from tradenexus.journal.repository import (
    load_signals,
    load_signals_paginated,
    load_alerts_paginated,
    export_signals_to_csv,
    export_alert_log_to_csv,
    export_trades_to_csv,
    clear_backtest_results,
    clear_demo_trades,
    clear_all_journal_data
)
from tradenexus.backtest.engine import run_mtf_backtest
from tradenexus.backtest.metrics import calculate_backtest_metrics
from tradenexus.ui.components import (
    render_backtest_metrics_panel,
    render_breakdown_tables
)

logger = logging.getLogger(__name__)

def render_strategy_lab_tab(ticker: str, tf_dfs: dict):
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
