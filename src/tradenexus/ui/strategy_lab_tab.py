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
import datetime
from tradenexus.optimization.optimizer import run_walk_forward_optimization
from tradenexus.optimization.optimization_repository import (
    load_optimization_runs,
    load_optimization_results,
    load_parameter_recommendations
)
from tradenexus.ui.components import (
    render_backtest_metrics_panel,
    render_breakdown_tables,
    render_recommendation_card,
    render_opt_results_table
)

logger = logging.getLogger(__name__)

def grid_meta_desc(est: int, limit: int) -> str:
    if est > limit:
        return f"sampled from {est}"
    return "brute force"

def render_strategy_lab_tab(ticker: str, tf_dfs: dict):
    st.header("📊 Strategy Lab")
    st.markdown("Analyze signal histories, check alert logs, and run backtests using non-repainting historical setups.")
    
    # Sub-tab structure
    tab_journal, tab_backtest, tab_opt = st.tabs(["📑 Signal Journal", "⚙️ Historical Backtest", "🧪 Walk-Forward Optimization"])
    
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
                    
    with tab_opt:
        st.subheader("🧪 Walk-Forward Parameters Optimization")
        st.info("Optimize strategy parameters using Walk-Forward splits to maximize expectancy and verify out-of-sample stability.")
        
        st.markdown("##### ⚙️ Step 1: Split & Holdout Configuration")
        col_wf1, col_wf2, col_wf3, col_wf4 = st.columns(4)
        with col_wf1:
            opt_train = st.number_input("Train Window (Bars)", min_value=50, max_value=2000, value=200, step=50)
        with col_wf2:
            opt_test = st.number_input("Test Window (Bars)", min_value=20, max_value=1000, value=50, step=10)
        with col_wf3:
            opt_step = st.number_input("Window Step Size (Bars)", min_value=10, max_value=1000, value=50, step=10)
        with col_wf4:
            opt_holdout = st.number_input("Final Holdout (Bars)", min_value=0, max_value=1000, value=0, step=50, help="Completely sets aside the latest bars for final out-of-sample validation.")

        col_wfc1, col_wfc2, col_wfc3 = st.columns(3)
        with col_wfc1:
            opt_max_combos = st.number_input("Max Grid Combinations", min_value=5, max_value=1000, value=50, step=5, help="Deterministic sampling limit to prevent execution slowdown.")
        with col_wfc2:
            opt_runtime = st.number_input("Max Runtime (Seconds)", min_value=30, max_value=1800, value=300, step=30)
        with col_wfc3:
            opt_seed = st.number_input("Sampling Seed", min_value=1, value=42, step=1)
            
        col_wfc_cost1, col_wfc_cost2 = st.columns(2)
        with col_wfc_cost1:
            opt_slippage = st.number_input("Opt Slippage (Points)", min_value=0.0, value=0.0, step=0.01)
        with col_wfc_cost2:
            opt_commission = st.number_input("Opt Commission (Pct %)", min_value=0.0, max_value=1.0, value=0.0, step=0.01)

        st.markdown("##### 🔍 Step 2: Configure Parameter Search Ranges")
        
        with st.expander("Expand to set Parameter Search Values (comma-separated lists)"):
            conf_range_str = st.text_input("Confluence Thresholds", "70, 75, 80")
            rr_range_str = st.text_input("Risk/Reward Ratio Limits", "1.5, 2.0")
            adx_range_str = st.text_input("ADX Strength Thresholds", "20, 25")
            
            try:
                conf_range = [float(x.strip()) for x in conf_range_str.split(",") if x.strip()]
                rr_range = [float(x.strip()) for x in rr_range_str.split(",") if x.strip()]
                adx_range = [float(x.strip()) for x in adx_range_str.split(",") if x.strip()]
            except ValueError:
                st.error("Invalid number lists provided. Using default search spaces.")
                conf_range = [70.0, 75.0, 80.0]
                rr_range = [1.5, 2.0]
                adx_range = [20.0, 25.0]
                
        # Est combos & Workload calculations
        est_combos = len(conf_range) * len(rr_range) * len(adx_range)
        eval_combos = min(est_combos, opt_max_combos)
        
        # Calculate estimated windows
        total_bars = len(tf_dfs.get("1h", pd.DataFrame()))
        opt_bars = total_bars - opt_holdout
        est_windows = 0
        if opt_bars >= opt_train + opt_test:
            est_windows = 1 + (opt_bars - opt_train - opt_test) // opt_step
            
        total_runs = eval_combos * est_windows
        
        if total_runs > 1000:
            wl_level = "HIGH 🔴"
            wl_color = "red"
        elif total_runs > 200:
            wl_level = "MEDIUM 🟡"
            wl_color = "orange"
        else:
            wl_level = "LOW 🟢"
            wl_color = "green"
            
        st.markdown(f"""
        <div style="background-color: #111827; border: 1px solid #374151; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <p style="margin: 0; color: #D1D5DB; font-size: 0.9rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">📋 Run Size Warning & Workload Assessment</p>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 10px;">
                <div><span style="color: #9CA3AF; font-size: 0.8rem;">Est. Grid Combinations</span><br/><strong style="font-size: 1.1rem; color: #F9FAFB;">{eval_combos} ({grid_meta_desc(est_combos, opt_max_combos)})</strong></div>
                <div><span style="color: #9CA3AF; font-size: 0.8rem;">Walk-Forward Windows</span><br/><strong style="font-size: 1.1rem; color: #F9FAFB;">{est_windows}</strong></div>
                <div><span style="color: #9CA3AF; font-size: 0.8rem;">Total Sim Runs</span><br/><strong style="font-size: 1.1rem; color: #F9FAFB;">{total_runs}</strong></div>
                <div><span style="color: #9CA3AF; font-size: 0.8rem;">Workload Level</span><br/><strong style="font-size: 1.1rem; color: {wl_color};">{wl_level}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if total_runs > 1000:
            st.warning("⚠️ Warning: Workload level is HIGH. Consider reducing the number of parameter ranges or window combinations to prevent browser performance bottlenecks.")
            
        st.markdown('<p style="color: #9CA3AF; font-size: 0.85rem; font-style: italic;">*Note: Recommended parameters are research outputs only. They are not applied to live settings automatically.</p>', unsafe_allow_html=True)
        
        if st.button("🚀 Run Walk-Forward Optimization", disabled=(est_windows == 0)):
            ranges_dict = {
                "confluence_threshold": conf_range,
                "rr_threshold": rr_range,
                "adx_threshold": adx_range
            }
            progress_bar = st.progress(0.0)
            
            def update_progress(val):
                progress_bar.progress(val)
                
            with st.spinner("Executing walk-forward search splits safely..."):
                try:
                    run_id = run_walk_forward_optimization(
                        symbol=ticker,
                        timeframe="1h",
                        start_date="2020-01-01",
                        end_date=datetime.date.today().isoformat(),
                        train_window_bars=opt_train,
                        test_window_bars=opt_test,
                        step_bars=opt_step,
                        ranges=ranges_dict,
                        max_combinations=opt_max_combos,
                        max_runtime_seconds=opt_runtime,
                        final_holdout_bars=opt_holdout,
                        sampling_seed=opt_seed,
                        slippage_points=opt_slippage,
                        commission_pct=opt_commission,
                        progress_cb=update_progress
                    )
                    
                    st.success(f"Optimization run completed! (ID: {run_id})")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Walk-Forward run failed: {str(ex)}")

        st.markdown("---")
        st.subheader("📋 Latest Parameter Recommendations & Runs")
        
        recs = load_parameter_recommendations(ticker, "1h")
        if recs:
            st.markdown("##### Recommended Settings Matrix")
            render_recommendation_card(recs[0])
            
            st.markdown("##### Walk-Forward Runs History")
            runs = load_optimization_runs(limit=5)
            if runs:
                df_runs = pd.DataFrame([{
                    "Run ID": r["run_id"],
                    "Symbol": r["symbol"],
                    "Timeframe": r["timeframe"],
                    "Status": r["status"],
                    "Total Combinations": r["grid_total_combinations"],
                    "Evaluated": r["grid_evaluated_combinations"],
                    "Method": r["grid_sampling_method"],
                    "Created At": r["created_at"]
                } for r in runs])
                st.dataframe(df_runs, use_container_width=True)
                
                selected_run = st.selectbox("Select Run to inspect window details", options=[r["run_id"] for r in runs])
                if selected_run:
                    results = load_optimization_results(selected_run)
                    render_opt_results_table(results)
            else:
                st.info("No runs history logged in database.")
        else:
            st.info("No walk-forward optimization runs have been executed for this asset and timeframe yet.")
