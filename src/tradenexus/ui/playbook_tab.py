import streamlit as st
import datetime
import uuid
import json
from tradenexus.playbook.playbook_models import Playbook, DailyTradingState
from tradenexus.playbook.playbook_repository import (
    get_active_playbook, save_playbook, load_playbooks, set_playbook_enabled,
    load_playbook_rule_events, get_daily_trading_state, save_daily_trading_state
)
from tradenexus.playbook.rule_engine import evaluate_playbook_rules
from tradenexus.playbook.playbook_explain import generate_playbook_summary

def render_playbook_tab(db_path: str = None):
    st.header("🛡️ Trading Playbook & Rule Enforcement")
    st.markdown("Enforce rule-based decision guardrails, daily risk limits, and cooldown timers before execution.")
    
    # Load active playbook
    active_pb = get_active_playbook(db_path)
    
    tab_overview, tab_editor, tab_sandbox = st.tabs([
        "📊 Overview & Monitoring", 
        "⚙️ Playbook Editor", 
        "🧪 Sandbox dry-run"
    ])
    
    # ------------------ OVERVIEW & MONITORING ------------------
    with tab_overview:
        col1, col2 = st.columns(2)
        
        # 1. Daily Trading State
        with col1:
            st.subheader("📈 Daily Discipline Tracker")
            date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            day_state = get_daily_trading_state(date_str, db_path)
            
            st.metric("Trades Executed Today", f"{day_state.trades_count} / {active_pb.max_trades_per_day}")
            st.metric("Losses Today", f"{day_state.losses_count} / {active_pb.max_losses_per_day}")
            st.metric("Consecutive Losses", f"{day_state.consecutive_losses} / {active_pb.max_consecutive_losses}")
            
            # Cooldown logic
            cooldown_active = False
            if active_pb.cooldown_minutes_after_loss > 0 and day_state.last_loss_time:
                try:
                    last_loss = datetime.datetime.fromisoformat(day_state.last_loss_time)
                    diff_mins = (datetime.datetime.utcnow() - last_loss).total_seconds() / 60.0
                    if diff_mins < active_pb.cooldown_minutes_after_loss:
                        cooldown_active = True
                        remaining = int(active_pb.cooldown_minutes_after_loss - diff_mins)
                        st.error(f"⏳ Cooldown Active: {remaining} minutes remaining before next trade.")
                except Exception:
                    pass
                    
            if not cooldown_active:
                st.success("✅ Risk limits & Cooldown verified. Ready to trade.")
                
            # Quick Simulation actions
            st.markdown("---")
            st.caption("Quick actions to simulate live journaling updates:")
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("➕ Trade"):
                    day_state.trades_count += 1
                    save_daily_trading_state(day_state, db_path)
                    st.rerun()
            with btn_col2:
                if st.button("➕ Loss"):
                    day_state.trades_count += 1
                    day_state.losses_count += 1
                    day_state.consecutive_losses += 1
                    day_state.last_loss_time = datetime.datetime.utcnow().isoformat()
                    save_daily_trading_state(day_state, db_path)
                    st.rerun()
            with btn_col3:
                if st.button("🔄 Reset"):
                    day_state = DailyTradingState(date=date_str)
                    save_daily_trading_state(day_state, db_path)
                    st.rerun()
                    
        # 2. Active Playbook Specs Info
        with col2:
            st.subheader("📜 Active Playbook Specifications")
            st.info(f"**Name:** {active_pb.name}\n\n"
                    f"**Min Confluence Score:** {active_pb.min_confluence_score}%\n\n"
                    f"**Min Risk-to-Reward:** {active_pb.min_rr:.2f}\n\n"
                    f"**Allowed Sessions:** {', '.join(active_pb.allowed_sessions) if active_pb.allowed_sessions else 'ANY'}\n\n"
                    f"**Allowed Timeframes:** {', '.join(active_pb.allowed_timeframes) if active_pb.allowed_timeframes else 'ANY'}\n\n"
                    f"**Blocked Regimes:** {', '.join(active_pb.blocked_regimes) if active_pb.blocked_regimes else 'None'}")
                    
        # 3. Violations Log
        st.markdown("---")
        st.subheader("🚨 Playbook Violations & Event Logs")
        events = load_playbook_rule_events(50, db_path)
        if not events:
            st.info("No playbook violations or events logged.")
        else:
            event_rows = []
            for ev in events:
                try:
                    details = json.loads(ev.details_json)
                    msg = details.get("message", "")
                except Exception:
                    msg = ev.details_json
                event_rows.append({
                    "Timestamp": ev.created_at,
                    "Symbol": ev.symbol,
                    "Rule": ev.rule_name,
                    "Type": ev.event_type,
                    "Decision": ev.decision_state,
                    "Details": msg
                })
            st.dataframe(event_rows, use_container_width=True)

    # ------------------ PLAYBOOK EDITOR ------------------
    with tab_editor:
        st.subheader("Modify Active Playbook Settings")
        with st.form("playbook_edit_form"):
            pb_name = st.text_input("Playbook Name", value=active_pb.name)
            pb_enabled = st.checkbox("Enabled", value=active_pb.enabled == 1)
            
            col_left, col_right = st.columns(2)
            with col_left:
                pb_symbols = st.text_input("Allowed Symbols (comma-separated)", value=", ".join(active_pb.allowed_symbols))
                pb_tfs = st.text_input("Allowed Timeframes (comma-separated)", value=", ".join(active_pb.allowed_timeframes))
                pb_setups = st.text_input("Allowed Setups (comma-separated)", value=", ".join(active_pb.allowed_setup_types))
                pb_min_conf = st.number_input("Minimum Confluence Score (%)", min_value=0.0, max_value=100.0, value=active_pb.min_confluence_score)
                pb_min_rr = st.number_input("Minimum RR Ratio", min_value=0.5, max_value=10.0, value=active_pb.min_rr, step=0.1)
                
            with col_right:
                pb_sessions = st.multiselect("Allowed Sessions", options=["ASIAN", "LONDON", "NEWYORK"], default=active_pb.allowed_sessions)
                pb_allowed_regimes = st.multiselect("Allowed Regimes", options=["TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS"], default=active_pb.allowed_regimes)
                pb_blocked_regimes = st.multiselect("Blocked Regimes", options=["TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS"], default=active_pb.blocked_regimes)
                pb_max_trades = st.number_input("Max Daily Trades", min_value=0, max_value=100, value=active_pb.max_trades_per_day)
                pb_max_losses = st.number_input("Max Daily Losses", min_value=0, max_value=100, value=active_pb.max_losses_per_day)
                pb_max_consec = st.number_input("Max Consecutive Losses", min_value=0, max_value=100, value=active_pb.max_consecutive_losses)
                pb_cooldown = st.number_input("Cooldown Minutes after Loss", min_value=0, max_value=1440, value=active_pb.cooldown_minutes_after_loss)
                
            pb_notes = st.text_area("Playbook Notes", value=active_pb.notes)
            
            submit_edit = st.form_submit_button("💾 Save Playbook Changes")
            if submit_edit:
                sym_list = [s.strip() for s in pb_symbols.split(",") if s.strip()]
                tf_list = [t.strip() for t in pb_tfs.split(",") if t.strip()]
                setup_list = [setp.strip() for setp in pb_setups.split(",") if setp.strip()]
                
                updated_pb = Playbook(
                    playbook_id=active_pb.playbook_id,
                    name=pb_name,
                    enabled=1 if pb_enabled else 0,
                    allowed_symbols=sym_list,
                    allowed_timeframes=tf_list,
                    allowed_setup_types=setup_list,
                    min_confluence_score=pb_min_conf,
                    min_rr=pb_min_rr,
                    allowed_regimes=pb_allowed_regimes,
                    blocked_regimes=pb_blocked_regimes,
                    max_trades_per_day=pb_max_trades,
                    max_losses_per_day=pb_max_losses,
                    max_consecutive_losses=pb_max_consec,
                    allowed_sessions=pb_sessions,
                    cooldown_minutes_after_loss=pb_cooldown,
                    notes=pb_notes,
                    created_at=active_pb.created_at
                )
                save_playbook(updated_pb, db_path)
                st.success("Playbook updated successfully!")
                st.rerun()

    # ------------------ SANDBOX DRY-RUN ------------------
    with tab_sandbox:
        st.subheader("🧪 Dry-Run Playbook Tester")
        st.markdown("Test rules and evaluate mock setups sandbox-style without writing to database.")
        
        with st.form("sandbox_form"):
            sand_symbol = st.text_input("Mock Symbol", value="BTC-USD")
            sand_tf = st.selectbox("Mock Timeframe", options=["15m", "1h", "4h", "1d"], index=1)
            sand_setup = st.selectbox("Mock Setup Type", options=["TREND_FOLLOWING", "COUNTER_TREND_SCALP", "NONE"], index=0)
            sand_conf = st.slider("Mock Confluence Score", min_value=0, max_value=100, value=75)
            sand_rr = st.slider("Mock Risk-to-Reward Ratio", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
            sand_regime = st.selectbox("Mock Market Regime", options=["TRENDING_UP", "TRENDING_DOWN", "SIDEWAYS"], index=0)
            sand_hour = st.slider("Mock Hour (UTC)", min_value=0, max_value=23, value=12)
            
            submit_sand = st.form_submit_button("🔍 Run Playbook Test")
            if submit_sand:
                mock_time = datetime.datetime.utcnow().replace(hour=sand_hour)
                status, passed, warnings, violations = evaluate_playbook_rules(
                    playbook=active_pb,
                    symbol=sand_symbol,
                    timeframe=sand_tf,
                    setup_type=sand_setup,
                    confluence_score=sand_conf,
                    rr=sand_rr,
                    market_regime=sand_regime,
                    current_time_utc=mock_time,
                    db_path=db_path
                )
                
                st.markdown("### Evaluation Results")
                summary = generate_playbook_summary(status, passed, warnings, violations)
                
                if status == "PASS":
                    st.success(summary)
                elif status == "WARNING":
                    st.warning(summary)
                else:
                    st.error(summary)
