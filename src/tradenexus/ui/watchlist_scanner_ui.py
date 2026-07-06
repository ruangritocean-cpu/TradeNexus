import streamlit as st
import pandas as pd
import json
import datetime
from tradenexus.scanner.watchlist import load_watchlist, save_watchlist
from tradenexus.scanner.scheduler import trigger_scheduled_scan, get_scheduler_status
from tradenexus.scanner.scan_repository import load_scan_runs, load_scan_results_for_run, load_scan_results_paginated
from tradenexus.ui.watchlist_helpers import sort_top_actionable_setups, count_warnings_in_results

def render_watchlist_scanner_tab(db_path: str = None, watchlist_path: str = None):
    st.header("📡 Watchlist Scanner Command Center")
    st.markdown("Monitor and scan multiple assets across preferred timeframes sequentially using the decision engine.")
    
    # ----------------- 1. WATCHLIST CONTROLS & TABLE -----------------
    st.subheader("📋 Watchlist Configurations")
    watchlist = load_watchlist(watchlist_path)
    
    # Render Watchlist editor
    with st.expander("⚙️ Manage Watchlist Symbols", expanded=False):
        # 1A. Add new symbol form
        with st.form("add_symbol_form"):
            st.markdown("##### Add New Watchlist Symbol")
            col_add1, col_add2, col_add3 = st.columns(3)
            with col_add1:
                new_symbol = st.text_input("Yahoo Finance Ticker (e.g. GC=F)", placeholder="GC=F")
            with col_add2:
                new_display = st.text_input("Display Name", placeholder="Gold Future")
            with col_add3:
                new_class = st.selectbox("Asset Class", options=["Commodities", "Indices", "Crypto", "Forex", "Equities"])
                
            col_add4, col_add5, col_add6 = st.columns(3)
            with col_add4:
                new_tfs = st.multiselect("Preferred Timeframes", options=["15m", "1h", "4h", "1d"], default=["1h", "4h"])
            with col_add5:
                new_conf = st.number_input("Min Confluence Score (%)", min_value=10.0, max_value=100.0, value=70.0, step=5.0)
            with col_add6:
                new_rr = st.number_input("Min Risk/Reward (RR)", min_value=1.0, max_value=5.0, value=1.5, step=0.1)
                
            submit_add = st.form_submit_button("➕ Add Asset to Watchlist")
            if submit_add and new_symbol:
                # Check duplicate
                if any(x["symbol"] == new_symbol for x in watchlist):
                    st.error(f"Symbol {new_symbol} already exists in watchlist.")
                else:
                    new_item = {
                        "symbol": new_symbol,
                        "display_name": new_display or new_symbol,
                        "asset_class": new_class,
                        "enabled": True,
                        "preferred_timeframes": new_tfs or ["1h"],
                        "min_confluence_score": new_conf,
                        "min_rr": new_rr,
                        "alert_enabled": True,
                        "alert_ready_enabled": False,
                        "alert_entry_enabled": True,
                        "notes": ""
                    }
                    watchlist.append(new_item)
                    save_watchlist(watchlist, watchlist_path)
                    st.success(f"Added {new_symbol} to watchlist successfully!")
                    st.rerun()
                    
        # 1B. Edit existing items
        st.markdown("##### Edit Watchlist Properties")
        if not watchlist:
            st.info("Watchlist is empty.")
        else:
            symbols_list = [x["symbol"] for x in watchlist]
            selected_sym = st.selectbox("Select Symbol to Edit", options=symbols_list)
            
            # Find item
            item_idx = next(i for i, x in enumerate(watchlist) if x["symbol"] == selected_sym)
            item = watchlist[item_idx]
            
            col_ed1, col_ed2, col_ed3 = st.columns(3)
            with col_ed1:
                item["enabled"] = st.checkbox("Enabled", value=item.get("enabled", True), key=f"en_{selected_sym}")
            with col_ed2:
                item["alert_enabled"] = st.checkbox("Alerts Enabled", value=item.get("alert_enabled", True), key=f"al_{selected_sym}")
            with col_ed3:
                item["alert_ready_enabled"] = st.checkbox("Alert on READY", value=item.get("alert_ready_enabled", False), key=f"al_ready_{selected_sym}")
                
            col_ed4, col_ed5, col_ed6 = st.columns(3)
            with col_ed4:
                item["alert_entry_enabled"] = st.checkbox("Alert on ENTRY TRIGGERED", value=item.get("alert_entry_enabled", True), key=f"al_entry_{selected_sym}")
            with col_ed5:
                item["min_confluence_score"] = st.number_input("Min Confluence Score", min_value=10.0, max_value=100.0, value=float(item.get("min_confluence_score", 70.0)), key=f"mc_{selected_sym}")
            with col_ed6:
                item["min_rr"] = st.number_input("Min RR Ratio", min_value=1.0, max_value=5.0, value=float(item.get("min_rr", 1.5)), key=f"mr_{selected_sym}")
                
            item["notes"] = st.text_input("Notes", value=item.get("notes", ""), key=f"nt_{selected_sym}")
            
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                if st.button("💾 Save Changes", key=f"sv_{selected_sym}"):
                    save_watchlist(watchlist, watchlist_path)
                    st.success(f"Saved changes for {selected_sym} successfully!")
                    st.rerun()
            with col_save2:
                if st.button("❌ Remove Asset", key=f"rm_{selected_sym}"):
                    watchlist.pop(item_idx)
                    save_watchlist(watchlist, watchlist_path)
                    st.warning(f"Removed {selected_sym} from watchlist.")
                    st.rerun()

    # Render Watchlist Display Table
    df_wl = pd.DataFrame([{
        "Ticker": x["symbol"],
        "Name": x["display_name"],
        "Class": x["asset_class"],
        "Enabled": "✅ Yes" if x.get("enabled", True) else "❌ No",
        "Preferred TFs": ", ".join(x.get("preferred_timeframes", ["1h"])),
        "Min Conf": f"{x.get('min_confluence_score', 70.0):.1f}%",
        "Min RR": f"{x.get('min_rr', 1.5):.2f}",
        "Alerts": "🔔 On" if x.get("alert_enabled", True) else "🔕 Off",
        "Notes": x.get("notes", "")
    } for x in watchlist])
    st.dataframe(df_wl, use_container_width=True)

    # ----------------- 2. SCHEDULER & MANUAL SCANNER -----------------
    st.markdown("---")
    st.subheader("⚙️ Scanner Scheduler")
    
    col_sc1, col_sc2, col_sc3 = st.columns(3)
    with col_sc1:
        max_scan = st.number_input("Max Symbols Per Scan", min_value=1, max_value=50, value=15, step=1)
    with col_sc2:
        scan_interval = st.number_input("Min Seconds Between Scans", min_value=5, max_value=3600, value=30, step=5)
    with col_sc3:
        force_candles = st.checkbox("Force Scan Open Candles", value=False, help="Unconditional scan overrides the Closed Candle Guard (warning: can repaint)")
        
    status = get_scheduler_status()
    st.info(f"**Scheduler State:** {status['scheduler_state']} | **Last Run RunID:** {status['last_scan_run_id'] or 'N/A'}")
    if status['last_scan_started_at']:
        st.markdown(f"*Last Scan Started At:* `{status['last_scan_started_at']}`")
    if status['last_scan_finished_at']:
        st.markdown(f"*Last Scan Finished At:* `{status['last_scan_finished_at']}`")
    if status['last_error']:
        st.error(f"**Last Error:** {status['last_error']}")
        
    discord_url = st.session_state.get("line_token", "")
    tg_token = st.session_state.get("tg_token", "")
    tg_chat = st.session_state.get("tg_chat_id", "")
    
    # Manual scan button
    if st.button("🚀 Trigger Manual Watchlist Scan"):
        with st.spinner("Executing sequential asset scans..."):
            res = trigger_scheduled_scan(
                db_path=db_path,
                watchlist_path=watchlist_path,
                discord_webhook=discord_url,
                tg_bot_token=tg_token,
                tg_chat_id=tg_chat,
                max_symbols=max_scan,
                min_seconds_between_scans=scan_interval,
                force_all_candles=force_candles
            )
            
            if res["status"] == "COMPLETED":
                st.success(f"Scan run {res['scan_run_id']} finished successfully!")
                st.rerun()
            elif res["status"] == "SKIPPED_OVERLAP":
                st.warning("Scan skipped: another scan is currently in progress.")
            else:
                st.error(f"Scan failed/skipped: {res.get('error_message', 'Unknown Error')}")
                
    # ----------------- 3. TOP ACTIONABLE SETUPS PANEL -----------------
    st.markdown("---")
    st.subheader("🔥 Top Actionable Setups")
    
    # Load scan results of the latest completed run
    runs = load_scan_runs(limit=1, db_path=db_path)
    if not runs:
        st.info("No scan runs recorded yet. Trigger a scan above to populate.")
    else:
        latest_run_id = runs[0].scan_run_id
        latest_results = load_scan_results_for_run(latest_run_id, db_path=db_path)
        actionable_setups = sort_top_actionable_setups(latest_results)
        
        if not actionable_setups:
            st.info("No actionable entry signals (`ENTRY TRIGGERED` or `READY`) found in the latest scan.")
        else:
            # Custom styled dashboard metrics cards
            cols = st.columns(min(len(actionable_setups), 4))
            for i, setup in enumerate(actionable_setups[:4]):
                with cols[i]:
                    symbol = setup.symbol
                    timeframe = setup.timeframe
                    state = setup.decision_state
                    direction = setup.direction
                    score = setup.confluence_score
                    rr = setup.rr_tp1
                    regime = setup.primary_regime
                    
                    bg_color = "rgba(52, 211, 153, 0.15)" if direction == "BUY" else "rgba(248, 113, 113, 0.15)"
                    border_color = "#34D399" if direction == "BUY" else "#F87171"
                    text_color = "#34D399" if direction == "BUY" else "#F87171"
                    
                    st.markdown(
                        f"""
                        <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px; padding: 15px; text-align: center;">
                            <h4 style="margin: 0; color: #FFFFFF;">{symbol} ({timeframe})</h4>
                            <p style="margin: 5px 0; color: {text_color}; font-size: 1.1em; font-weight: bold;">{state} ({direction})</p>
                            <div style="font-size: 0.9em; color: #E5E7EB; margin-top: 10px;">
                                <div><b>Confluence:</b> {score:.1f}%</div>
                                <div><b>RR Target:</b> {rr:.2f}R</div>
                                <div><b>Regime:</b> {regime}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Explain brief helper
                    import json
                    warnings_raw = []
                    if setup.warnings_json:
                        try:
                            warnings_raw = json.loads(setup.warnings_json)
                        except Exception:
                            warnings_raw = []
                            
                    brief_data = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "decision_state": state,
                        "direction": direction,
                        "alignment_type": setup.alignment_type,
                        "confluence_score": score,
                        "primary_regime": regime,
                        "regime_flags": json.loads(setup.regime_flags_json) if setup.regime_flags_json else [],
                        "entry": 0.0,
                        "sl": 0.0,
                        "tp1": 0.0,
                        "tp2": 0.0,
                        "rr_tp1": rr,
                        "warnings": warnings_raw,
                        "portfolio_risk_status": "BLOCKED" if setup.alert_status == "BLOCKED_BY_PORTFOLIO_RISK" else "OK"
                    }
                    
                    if setup.signal_id:
                        from tradenexus.journal.repository import load_signal_by_id
                        sig = load_signal_by_id(setup.signal_id, db_path)
                        if sig:
                            brief_data["entry"] = sig.entry
                            brief_data["sl"] = sig.sl
                            brief_data["tp1"] = sig.tp1
                            brief_data["tp2"] = sig.tp2
                            
                    from tradenexus.explain.decision_brief import generate_decision_brief
                    from tradenexus.explain.templates import format_full_brief
                    
                    brief = generate_decision_brief(brief_data, db_path)
                    with st.expander(f"🔍 Explain {symbol}", expanded=False):
                        st.markdown(format_full_brief(brief))

    # ----------------- 4. SCAN RUNS LOG -----------------
    st.markdown("---")
    st.subheader("📜 Historical Scan Logs")
    
    historical_runs = load_scan_runs(limit=10, db_path=db_path)
    if not historical_runs:
        st.info("No historical scan runs logged.")
    else:
        run_options = {r.scan_run_id: f"{r.scan_run_id} | Status: {r.status} | {r.started_at}" for r in historical_runs}
        selected_run_id = st.selectbox("Inspect Scan Run Results", options=list(run_options.keys()), format_func=lambda x: run_options[x])
        
        results_for_run = load_scan_results_for_run(selected_run_id, db_path=db_path)
        
        # Display Run summary metrics
        selected_run = next(r for r in historical_runs if r.scan_run_id == selected_run_id)
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            st.metric("Total Assets", selected_run.total_symbols)
        with col_m2:
            st.metric("Success", selected_run.success_count)
        with col_m3:
            st.metric("Warnings", selected_run.warning_count)
        with col_m4:
            st.metric("Errors", selected_run.error_count)
        with col_m5:
            st.metric("Skipped", selected_run.skipped_count)
            
        if not results_for_run:
            st.info("No asset scan results recorded for this run.")
        else:
            df_res = pd.DataFrame([{
                "Symbol": r.symbol,
                "Timeframe": r.timeframe,
                "Status": r.symbol_status,
                "Decision": r.decision_state,
                "Direction": r.direction,
                "Confluence": f"{r.confluence_score:.1f}%",
                "RR": f"{r.rr_tp1:.2f}R",
                "Regime": r.primary_regime,
                "Alert": r.alert_status,
                "Journal": r.journal_status,
                "Error": r.error_message
            } for r in results_for_run])
            
            st.dataframe(df_res, use_container_width=True)
