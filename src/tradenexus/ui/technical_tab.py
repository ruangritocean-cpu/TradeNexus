import streamlit as st
import pandas as pd
import numpy as np
import datetime
import logging

from tradenexus.pipeline.indicator_pipeline import calculate_all_indicators
from tradenexus.pipeline.decision_pipeline import evaluate_decision_and_scoring
from tradenexus.ui.components import (
    render_trading_strategy_panel,
    render_top_metrics_bar,
    render_ttd_dashboard
)
from tradenexus.ui.charts import draw_advanced_charts
from tradenexus.explain.decision_brief import generate_decision_brief
from tradenexus.explain.templates import format_full_brief
from tradenexus.signals.state import get_active_trade, update_trade_status

logger = logging.getLogger(__name__)

def render_technical_tab(ticker: str, tf_dfs: dict, tf_warnings: dict):
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
    timeframes = ["15m", "1h", "4h", "1d"]
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
        return
        
    latest_row = df_to_plot.iloc[-1]
    latest_row_dict = latest_row.to_dict()
    
    # Extract latest row for resampled dfs
    latest_15m_dict = tf_dfs["15m"].iloc[-1].to_dict() if not tf_dfs["15m"].empty else {}
    latest_1h_dict = tf_dfs["1h"].iloc[-1].to_dict() if not tf_dfs["1h"].empty else {}
    latest_4h_dict = tf_dfs["4h"].iloc[-1].to_dict() if not tf_dfs["4h"].empty else {}
    latest_1d_dict = tf_dfs["1d"].iloc[-1].to_dict() if not tf_dfs["1d"].empty else {}
    
    # Run unified pipeline for scoring and decision state
    try:
        dec_res = evaluate_decision_and_scoring(
            latest_15m=latest_15m_dict,
            latest_1h=latest_1h_dict,
            latest_4h=latest_4h_dict,
            latest_1d=latest_1d_dict,
            timeframe=selected_tf,
            min_confluence_score=70.0,
            min_rr=1.5
        )
    except Exception as exc:
        st.error("⚠️ ระบบวิเคราะห์การตัดสินใจสอดคล้องขัดข้องชั่วคราว (Decision Pipeline failed). หน้ากราฟราคาหลักและอินดิเคเตอร์ยังสามารถทำงานได้ตามปกติ")
        logger.error(f"decision_pipeline_failed: symbol={ticker}, timeframe={selected_tf}, error={str(exc)}")
        dec_res = {
            "decision_state": "NO TRADE",
            "direction": "NEUTRAL",
            "alignment_type": "CONFLICTED",
            "confluence_score": 0.0,
            "directional_score": 0.0,
            "quality_score": 0.0,
            "reasons": [],
            "warnings": [f"Pipeline computation error: {str(exc)}"],
            "rr_tp1": 0.0,
            "primary_regime": "UNKNOWN",
            "regime_flags": []
        }
    
    decision_state = dec_res["decision_state"]
    base_dec = dec_res["direction"]
    alignment_type = dec_res["alignment_type"]
    confluence_score = dec_res["confluence_score"]
    primary_regime = dec_res["primary_regime"]
    regime_flags = dec_res["regime_flags"]
    
    # 2. Risk Target calculation & veto logic
    support_val = latest_row.get("Support_Level", 0.0)
    resistance_val = latest_row.get("Resistance_Level", 0.0)
    atr_val = latest_row.get("ATR", 0.0)
    
    from tradenexus.signals.risk import validate_trade_risk
    risk_result = validate_trade_risk(
        price=latest_row["Close"],
        decision=base_dec,
        support=support_val,
        resistance=resistance_val,
        atr=atr_val,
        rr_min=1.5
    )
    
    strategy = {
        "Decision": decision_state,
        "Direction": base_dec,
        "AlignmentType": alignment_type,
        "ConfluenceScore": confluence_score,
        "DirectionalScore": dec_res["directional_score"],
        "QualityScore": dec_res["quality_score"],
        "Entry": risk_result["Entry"],
        "StopLoss": risk_result["StopLoss"],
        "TakeProfit1": risk_result["TakeProfit1"],
        "TakeProfit2": risk_result["TakeProfit2"],
        "RR_TP1": risk_result["RR_TP1"],
        "RR_TP2": risk_result["RR_TP2"],
        "Reasons": dec_res["reasons"],
        "Warnings": dec_res["warnings"],
        "Vetoed": risk_result["Vetoed"],
        "VetoReason": risk_result["VetoReason"],
        "DataQualityWarning": (tf_warnings.get(selected_tf, "") != ""),
        "Regime": primary_regime,
        "RegimeScore": latest_row.get("regime_score", 0.0),
        "RegimeFlags": ",".join(regime_flags),
        "VolumeConfirmation": latest_row.get("Volume_Confirmation", "NEUTRAL"),
        "VwapAlignment": "BULLISH" if latest_row["Close"] > latest_row.get("VWAP", latest_row["Close"]) else "BEARISH",
        "BOS": latest_row.get("BOS_Present", 0),
        "CHOCH": latest_row.get("CHOCH_Present", 0),
        "FVG": latest_row.get("FVG_Present", 0),
        "LiquiditySweep": latest_row.get("Liquidity_Sweep", 0)
    }
    
    # Render premium Decision Card
    render_trading_strategy_panel(strategy)
    
    # Render Playbook Enforcer status below Decision Card
    try:
        from tradenexus.playbook.playbook_repository import get_active_playbook
        from tradenexus.playbook.rule_engine import evaluate_playbook_rules
        from tradenexus.playbook.playbook_explain import generate_playbook_summary
        
        playbook = get_active_playbook()
        pb_status, pb_passed, pb_warnings, pb_violations = evaluate_playbook_rules(
            playbook=playbook,
            symbol=ticker,
            timeframe=selected_tf,
            setup_type=alignment_type,
            confluence_score=confluence_score,
            rr=risk_result["RR_TP1"],
            market_regime=primary_regime
        )
        
        pb_summary = generate_playbook_summary(pb_status, pb_passed, pb_warnings, pb_violations)
        with st.expander(f"🛡️ Playbook Enforcement Status: {pb_status}", expanded=(pb_status != "PASS")):
            if pb_status == "PASS":
                st.success(pb_summary)
            elif pb_status == "WARNING":
                st.warning(pb_summary)
            else:
                st.error(pb_summary)
    except Exception as pb_err:
        logger.warning(f"Playbook evaluation failed in UI: {pb_err}")
    
    # Render deterministic Decision Brief explanation panel
    brief_data = {
        "symbol": ticker,
        "timeframe": selected_tf,
        "decision_state": decision_state,
        "direction": base_dec,
        "alignment_type": alignment_type,
        "confluence_score": strategy["ConfluenceScore"],
        "primary_regime": primary_regime,
        "regime_flags": regime_flags,
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
        if active_trade:
            st.info(f"🛡️ **Active Position Info:** {active_trade['direction']} {active_trade['symbol']} entered at ${active_trade['entry']:,.2f} on {active_trade['entry_time']}.")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                if st.button("Simulate TP1 Hit"):
                    update_trade_status("TP1_HIT")
                    st.success("Trade status updated to TP1_HIT!")
                    st.rerun()
            with col_m2:
                if st.button("Simulate TP2 Hit (Closes Position)"):
                    update_trade_status("TP2_HIT")
                    st.success("Position closed at TP2!")
                    st.rerun()
                    
            col_m3, col_m4 = st.columns(2)
            with col_m3:
                if st.button("Simulate SL Hit (Closes Position)"):
                    update_trade_status("SL_HIT")
                    st.error("Position stopped out at SL.")
                    st.rerun()
            with col_m4:
                if st.button("Close Position Manually"):
                    update_trade_status("CLOSED")
                    st.info("Position closed manually.")
                    st.rerun()
                    
    # ----------------- DRAW CHARTS -----------------
    st.markdown("---")
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        show_regime = st.checkbox("Show Market Regime Shading", value=True)
    with col_opt2:
        show_bos_choch = st.checkbox("Show BOS / CHOCH Breaks", value=True)
    with col_opt3:
        show_eql_eqh = st.checkbox("Show Equal Highs/Lows Zones", value=True)
        
    try:
        draw_advanced_charts(
            df=df_to_plot,
            ticker=ticker,
            timeframe=selected_tf,
            strategy=strategy,
            show_vwap=True,
            show_fvg=True,
            show_ob=True,
            show_sweeps=True,
            show_bos_choch=show_bos_choch,
            show_eql_eqh=show_eql_eqh,
            show_market_regime_shading=show_regime
        )
    except TypeError as exc:
        st.error("Advanced chart rendering failed because chart overlay arguments do not match.")
        st.exception(exc)
    except Exception as exc:
        st.error("Advanced chart rendering failed. Decision Card and indicators are still available.")
        st.exception(exc)
    
    # Data Explorer expander
    with st.expander("📄 Data Explorer"):
        st.markdown(f"### Latest 10 Rows of Calculated Data ({selected_tf})")
        display_cols = ["Open", "High", "Low", "Close", "Volume", "EMA_Fast", "EMA_Slow", "Support_Level", "Resistance_Level", "MCDX_Proxy", "MCDX_Smart", "Support_Source", "Resistance_Source"]
        existing_cols = [c for c in display_cols if c in df_to_plot.columns]
        st.dataframe(df_to_plot[existing_cols].tail(10), use_container_width=True)
