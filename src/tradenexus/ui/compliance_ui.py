import streamlit as st
import datetime
import json
from tradenexus.reports.compliance_engine import generate_compliance_report
from tradenexus.reports.report_export import export_report_to_csv, export_report_to_json
from tradenexus.workspace.workspace_context import get_active_workspace_id

def render_compliance_report_tab(db_path: str = None):
    st.header("📊 Trading Plan Compliance Report")
    st.markdown("Assess trading discipline, Playbook violations, risk limit breaches, and optimized recommendation alignment.")
    
    # 1. Date Range Filters
    st.markdown("### 🧭 Filter Report Date Range")
    date_filter = st.selectbox(
        "Select Date Range / ช่วงเวลา",
        ["Today", "Last 7 Days", "Last 30 Days", "Custom Range"]
    )
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    if date_filter == "Today":
        start_dt = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_filter == "Last 7 Days":
        start_dt = now_utc - datetime.timedelta(days=7)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_filter == "Last 30 Days":
        start_dt = now_utc - datetime.timedelta(days=30)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Custom Range
        col_start, col_end = st.columns(2)
        with col_start:
            start_date_val = st.date_input("Start Date", value=(now_utc - datetime.timedelta(days=30)).date())
        with col_end:
            end_date_val = st.date_input("End Date", value=now_utc.date())
            
        start_dt = datetime.datetime.combine(start_date_val, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date_val, datetime.time.max)
        
    start_iso = start_dt.isoformat() + "Z"
    end_iso = end_dt.isoformat() + "Z"
    
    st.caption(f"📅 Running evaluation from **{start_iso}** to **{end_iso}** (all times are parsed in UTC)")
    
    workspace_id = get_active_workspace_id()
    
    # 2. Generate Compliance Report
    report = generate_compliance_report(workspace_id, start_iso, end_iso, db_path)
    
    # 3. Compliance Score Radial Display
    score = report.compliance_score
    
    if score >= 90.0:
        score_color = "#10B981"  # Emerald green
        score_status = "🏆 Excellent Discipline (วินัยยอดเยี่ยม)"
    elif score >= 80.0:
        score_color = "#3B82F6"  # Blue
        score_status = "📈 Good Discipline (วินัยดี)"
    elif score >= 60.0:
        score_color = "#F59E0B"  # Amber
        score_status = "⚠️ Minor Breaches (ควรระวังวินัยหลุด)"
    else:
        score_color = "#EF4444"  # Red
        score_status = "🚨 Low Discipline (วินัยหลุดแผนบ่อยครั้ง)"
        
    st.markdown(f"""
        <div style="background-color: #1F2937; border-radius: 12px; padding: 25px; text-align: center; border-left: 5px solid {score_color}; margin-bottom: 25px;">
            <p style="margin: 0; font-size: 1.1rem; color: #9CA3AF; font-weight: 500;">Plan Compliance Score</p>
            <h1 style="margin: 5px 0; font-size: 3.5rem; color: {score_color}; font-weight: 800;">{score:.1f} %</h1>
            <p style="margin: 0; font-size: 1.2rem; color: #E5E7EB; font-weight: 600;">{score_status}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 4. Executive Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    m = report.metrics
    with col1:
        st.metric("Total Signals Scanned", m.total_signals)
        st.metric("Actionable Setups", m.actionable_signals)
    with col2:
        st.metric("Alerts Dispatched", m.alerts_sent)
        st.metric("Win Rate", f"{m.win_rate * 100:.1f}%")
    with col3:
        st.metric("Playbook Violations", m.playbook_violation_count)
        st.metric("Expectancy", f"{m.expectancy:.2f}R")
    with col4:
        st.metric("Risk Blocks", m.alerts_blocked_portfolio)
        st.metric("Max Drawdown", f"{m.max_drawdown:.2f}R")
        
    st.markdown("---")
    
    # Preset & Drift Dashboard
    try:
        details = json.loads(report.details_json)
    except Exception:
        details = {}
        
    active_preset_name = details.get("active_preset_name")
    if active_preset_name:
        st.markdown(f"### 📚 Active Strategy Preset: **{active_preset_name}**")
        drift_detected = details.get("preset_drift_detected", False)
        if drift_detected:
            st.error("⚠️ **Preset Configuration Drift Detected / ตรวจพบการตั้งค่าเบี่ยงเบนจากเทมเพลต**")
            drift_fields_str = details.get("preset_drift_fields_json", "[]")
            try:
                drift_fields = json.loads(drift_fields_str)
                for f in drift_fields:
                    st.markdown(f"- Field `{f['field_name']}` has drifted: Preset value was `{f['preset_value']}`, Current config value is `{f['current_value']}`")
            except Exception:
                pass
        else:
            st.success("✅ **Configuration matches active preset precisely (No Drift).**")
        st.markdown("---")

    # 5. Detail Breakdowns Tabs
    tab_violations, tab_portfolio, tab_quality, tab_recommendations = st.tabs([
        "🛡️ Playbook Violations",
        "🛑 Portfolio Risk Blocks",
        "🔍 Data Quality Warnings",
        "🔬 Optimization Alignment"
    ])
    
    try:
        details = json.loads(report.details_json)
    except Exception:
        details = {}
        
    with tab_violations:
        st.subheader("Playbook Discipline Rules Violations")
        violations = details.get("playbook_violations", [])
        if not violations:
            st.success("🎉 No playbook rule violations found within the selected period!")
        else:
            # Table view
            st.warning(f"Found {len(violations)} playbook violations:")
            for v in violations:
                try:
                    msg = json.loads(v.get("details", "{}")).get("message", "")
                except Exception:
                    msg = ""
                st.markdown(f"- **{v.get('symbol')}** @ {v.get('created_at')} -> **State: {v.get('decision_state')}**: {msg}")
                
        # Breakdowns stats
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            st.write(f"Session Violations: **{m.session_violations}**")
            st.write(f"Cooldown Violations: **{m.cooldown_violations}**")
        with col_v2:
            st.write(f"Low RR Ratio Violations: **{m.low_rr_violations}**")
            st.write(f"Low Confluence Violations: **{m.low_confluence_violations}**")
        with col_v3:
            st.write(f"Overtrading Warnings: **{m.overtrading_warnings}**")

    with tab_portfolio:
        st.subheader("Portfolio Risk Limit Blocks")
        blocks = details.get("portfolio_blocks", [])
        if not blocks:
            st.success("🎉 No portfolio risk limit blocks logged within this period!")
        else:
            st.error(f"Found {len(blocks)} portfolio risk blocks:")
            for b in blocks:
                st.markdown(f"- **{b.get('symbol')}** @ {b.get('created_at')}: 🚨 *{b.get('reason')}*")
                
    with tab_quality:
        st.subheader("Provider Data Quality Warnings")
        if m.signals_invalid_data == 0 and m.signals_data_warnings == 0:
            st.success("🎉 100% of provider signals contain valid, healthy pricing feeds!")
        else:
            st.warning(f"Data feed errors checklist:")
            st.write(f"Signals with completely invalid feed structure: **{m.signals_invalid_data}**")
            st.write(f"Signals with warming up or stale candle warnings: **{m.signals_data_warnings}**")
            
    with tab_recommendations:
        st.subheader("Walk-Forward Parameter Recommendations Alignment")
        recs = details.get("parameter_recommendation_alignment", [])
        if not recs:
            st.info("No active optimization parameters recommendations found for this workspace. Run Strategy Lab first.")
        else:
            st.write("Active parameters recommendations mapped to live scanned signals in this workspace:")
            for r in recs:
                st.markdown(f"- **{r.get('symbol')}** ({r.get('timeframe')}) -> Status: **{r.get('recommendation_status')}** (Robustness Score: `{r.get('robustness_score')}`)")
                
    st.markdown("---")
    
    # 6. Report Export
    st.markdown("### 📥 Export Compliance Report")
    csv_data = export_report_to_csv(report)
    json_data = export_report_to_json(report)
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="Download CSV Report",
            data=csv_data,
            file_name=f"compliance_report_{workspace_id}_{date_filter.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )
    with col_dl2:
        st.download_button(
            label="Download JSON Report",
            data=json_data,
            file_name=f"compliance_report_{workspace_id}_{date_filter.lower().replace(' ', '_')}.json",
            mime="application/json"
        )
