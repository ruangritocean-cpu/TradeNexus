import streamlit as st
import pandas as pd
import json
import datetime
import logging
from typing import List, Optional
import plotly.express as px

from tradenexus.portfolio.portfolio_repository import (
    load_portfolio_settings,
    save_portfolio_settings,
    load_all_symbol_profiles,
    save_symbol_profile,
    load_risk_events
)
from tradenexus.portfolio.risk_models import PortfolioSettings, SymbolRiskProfile
from tradenexus.portfolio.position_sizing import calculate_position_size
from tradenexus.portfolio.exposure import calculate_portfolio_exposure
from tradenexus.portfolio.correlation import calculate_returns_correlation
from tradenexus.portfolio.limits import check_portfolio_risk_limits
from tradenexus.scanner.watchlist import load_watchlist

logger = logging.getLogger(__name__)

def render_portfolio_ui(db_path: str = None, watchlist_path: str = None):
    try:
        st.header("🛡️ Portfolio Risk Command Center")
        st.markdown("Monitor exposure limits, evaluate position sizing, calculate correlation clustering, and edit risk policies.")
        
        # Load settings and exposure
        settings = load_portfolio_settings(db_path)
        exposure = calculate_portfolio_exposure(db_path, settings)
        
        # Load watchlist to compute correlation
        watchlist = load_watchlist(watchlist_path)
        watchlist_symbols = [x["symbol"] for x in watchlist if x.get("enabled", True)]
        
        correlation = calculate_returns_correlation(
            symbols=watchlist_symbols,
            lookback_bars=settings.correlation_lookback_bars,
            correlation_threshold=settings.correlation_threshold,
            cache_ttl_seconds=settings.correlation_cache_ttl_seconds
        )
        
        # Calculate limits status
        limits = check_portfolio_risk_limits(
            settings=settings,
            exposure=exposure,
            correlation=correlation
        )
        
        # ----------------- 1. METRICS HEADER BAR -----------------
        st.subheader("📊 Portfolio Risk Status")
        
        # Premium styled risk badge
        badge_colors = {
            "OK": ("rgba(52, 211, 153, 0.2)", "#34D399"),
            "WARNING": ("rgba(251, 191, 36, 0.2)", "#FBBF24"),
            "BLOCKED": ("rgba(248, 113, 113, 0.2)", "#F87171")
        }
        bg_col, txt_col = badge_colors.get(limits.risk_status, ("rgba(156, 163, 175, 0.2)", "#9CA3AF"))
        
        st.markdown(
            f"""
            <div style="background-color: {bg_col}; border: 1px solid {txt_col}; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 20px;">
                <span style="font-size: 1.1em; color: #E5E7EB;"><b>Portfolio Status:</b></span>
                <span style="color: {txt_col}; font-size: 1.3em; font-weight: bold; margin-left: 10px;">{limits.risk_status}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if limits.reasons:
            for r in limits.reasons:
                st.error(f"❌ {r}")
        if limits.warnings:
            for w in limits.warnings:
                st.warning(f"⚠️ {w}")
                
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric(
                label="Account Equity",
                value=f"${exposure.equity:,.2f}",
                delta=None
            )
        with col_m2:
            st.metric(
                label="Active Trades",
                value=f"{exposure.number_of_active_trades} / {settings.max_concurrent_trades}",
                delta=None
            )
        with col_m3:
            st.metric(
                label="Current Open Risk",
                value=f"${exposure.total_open_risk:,.2f}",
                delta=f"{exposure.total_open_risk_pct:.2f}% / {settings.max_total_open_risk_pct}%",
                delta_color="inverse"
            )
        with col_m4:
            st.metric(
                label="Realized Daily Loss/Gain",
                value=f"${exposure.realized_daily_risk:,.2f}",
                delta=f"Max Limit: {settings.max_daily_risk_pct}%",
                delta_color="normal"
            )
            
        # ----------------- 2. ASSET & SYMBOL EXPOSURE -----------------
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.subheader("🪙 Exposure by Symbol")
            if not exposure.risk_by_symbol:
                st.info("No symbol exposure active.")
            else:
                df_sym = pd.DataFrame([
                    {"Symbol": k, "Risk Amount ($)": v, "Risk Pct (%)": (v / exposure.equity * 100.0) if exposure.equity > 0 else 0.0}
                    for k, v in exposure.risk_by_symbol.items() if v > 0
                ]).sort_values(by="Risk Amount ($)", ascending=False)
                st.dataframe(df_sym, use_container_width=True)
                
        with col_exp2:
            st.subheader("💼 Exposure by Asset Class")
            if not exposure.risk_by_asset_class:
                st.info("No asset class exposure active.")
            else:
                df_class = pd.DataFrame([
                    {"Asset Class": k, "Risk Amount ($)": v, "Risk Pct (%)": (v / exposure.equity * 100.0) if exposure.equity > 0 else 0.0}
                    for k, v in exposure.risk_by_asset_class.items() if v > 0
                ]).sort_values(by="Risk Amount ($)", ascending=False)
                st.dataframe(df_class, use_container_width=True)
                
        # ----------------- 3. POSITION SIZING LAB -----------------
        st.markdown("---")
        st.subheader("🧮 Advanced Position Sizing Calculator")
        st.markdown("Compute exact share or contract quantities based on target risk budgets, point values, multipliers, and slippage penalties.")
        
        with st.expander("🛠️ Open Sizing Calculator", expanded=False):
            with st.form("calc_form"):
                col_calc1, col_calc2, col_calc3 = st.columns(3)
                with col_calc1:
                    c_entry = st.number_input("Entry Price", min_value=0.0001, value=100.0, step=1.0)
                with col_calc2:
                    c_sl = st.number_input("Stop Loss Price", min_value=0.0001, value=95.0, step=1.0)
                with col_calc3:
                    c_dir = st.selectbox("Direction", options=["BUY", "SELL"])
                    
                col_calc4, col_calc5, col_calc6 = st.columns(3)
                with col_calc4:
                    c_pv = st.number_input("Point Value", min_value=0.01, value=1.0, step=1.0)
                with col_calc5:
                    c_mult = st.number_input("Contract Multiplier", min_value=0.01, value=1.0, step=1.0)
                with col_calc6:
                    c_comm = st.number_input("Commission (Pct %)", min_value=0.0, max_value=5.0, value=0.0, step=0.01)
                    
                col_calc7, col_calc8, col_calc9 = st.columns(3)
                with col_calc7:
                    c_slip = st.number_input("Slippage (Points)", min_value=0.0, value=0.0, step=0.01)
                with col_calc8:
                    c_step = st.number_input("Position size step", min_value=0.0001, value=0.01, step=0.01)
                with col_calc9:
                    c_min = st.number_input("Min position size", min_value=0.0001, value=0.01, step=0.01)
                    
                c_tp1 = st.number_input("TP1 Target (Optional)", min_value=0.0, value=0.0)
                c_tp2 = st.number_input("TP2 Target (Optional)", min_value=0.0, value=0.0)
                
                calc_submit = st.form_submit_button("Calculate Position Size")
                if calc_submit:
                    calc_res = calculate_position_size(
                        account_equity=settings.account_equity,
                        risk_per_trade_pct=settings.risk_per_trade_pct,
                        entry=c_entry,
                        stop_loss=c_sl,
                        direction=c_dir,
                        point_value=c_pv,
                        contract_multiplier=c_mult,
                        commission_pct=c_comm,
                        slippage_points=c_slip,
                        min_position_size=c_min,
                        position_step=c_step,
                        tp1=c_tp1,
                        tp2=c_tp2
                    )
                    
                    if calc_res.sizing_status == "ERROR":
                        st.error(f"Sizing Failed: {calc_res.sizing_warning}")
                    else:
                        st.success("Calculated successfully!")
                        if calc_res.sizing_warning:
                            st.warning(calc_res.sizing_warning)
                        
                        df_c_res = pd.DataFrame([{
                            "Metric": "Risk Budget ($)", "Value": f"${calc_res.risk_amount:,.2f}"
                        }, {
                            "Metric": "Risk Points", "Value": f"{calc_res.risk_points:.4f}"
                        }, {
                            "Metric": "Position Size Units", "Value": f"{calc_res.position_size_units:.4f}"
                        }, {
                            "Metric": "Est Loss at SL ($)", "Value": f"${calc_res.estimated_loss_at_sl:,.2f}"
                        }, {
                            "Metric": "Est Profit TP1 ($)", "Value": f"${calc_res.estimated_profit_tp1:,.2f} (RR: {calc_res.r_multiple_tp1:.2f}R)"
                        }, {
                            "Metric": "Est Profit TP2 ($)", "Value": f"${calc_res.estimated_profit_tp2:,.2f} (RR: {calc_res.r_multiple_tp2:.2f}R)"
                        }])
                        st.table(df_c_res)
        
        # ----------------- 4. SYMBOL RISK PROFILES -----------------
        st.markdown("---")
        st.subheader("📑 Symbol Risk Profiles")
        
        profiles = load_all_symbol_profiles(db_path)
        
        with st.expander("⚙️ Manage Symbol Risk Profiles", expanded=False):
            with st.form("sym_form"):
                st.markdown("##### Add or Edit Symbol Profile")
                col_sym1, col_sym2, col_sym3 = st.columns(3)
                with col_sym1:
                    s_sym = st.text_input("Ticker Symbol (e.g. BTC-USD)")
                with col_sym2:
                    s_class = st.selectbox("Symbol Asset Class", options=["Crypto", "Commodities", "Indices", "Forex", "Equities"])
                with col_sym3:
                    s_pv = st.number_input("Point Value", min_value=0.001, value=1.0)
                    
                col_sym4, col_sym5, col_sym6 = st.columns(3)
                with col_sym4:
                    s_mult = st.number_input("Multiplier", min_value=0.001, value=1.0)
                with col_sym5:
                    s_min = st.number_input("Min size", min_value=0.0001, value=0.01)
                with col_sym6:
                    s_step = st.number_input("Size step", min_value=0.0001, value=0.01)
                    
                sym_submit = st.form_submit_button("Save Symbol Profile")
                if sym_submit and s_sym:
                    new_prof = SymbolRiskProfile(
                        symbol=s_sym,
                        asset_class=s_class,
                        point_value=s_pv,
                        contract_multiplier=s_mult,
                        min_position_size=s_min,
                        position_step=s_step
                    )
                    save_symbol_profile(new_prof, db_path)
                    st.success(f"Profile saved for {s_sym} successfully!")
                    st.rerun()
                    
        if not profiles:
            st.info("No custom symbol risk profiles configured. Defaults will apply.")
        else:
            df_profs = pd.DataFrame([{
                "Symbol": p.symbol,
                "Class": p.asset_class,
                "Point Value": p.point_value,
                "Multiplier": p.contract_multiplier,
                "Min Size": p.min_position_size,
                "Size Step": p.position_step,
                "Currency": p.currency
            } for p in profiles])
            st.dataframe(df_profs, use_container_width=True)
            
        # ----------------- 5. CORRELATION RISK -----------------
        st.markdown("---")
        st.subheader("🕸️ Watchlist Returns Correlation Matrix")
        
        if not correlation.correlation_matrix:
            st.info("No returns correlation data available.")
        else:
            df_corr = pd.DataFrame(correlation.correlation_matrix)
            try:
                fig_corr = px.imshow(
                    df_corr,
                    text_auto=".2f",
                    zmin=-1,
                    zmax=1,
                    color_continuous_scale="RdBu",
                    aspect="auto",
                    title="เมทริกซ์ความสัมพันธ์ส่วนต่างราคา (Watchlist Returns Correlation Matrix)"
                )
                fig_corr.update_layout(
                    height=420,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                st.plotly_chart(fig_corr, use_container_width=True)
            except Exception as px_err:
                logger.error(f"Plotly correlation rendering failed: {str(px_err)}")
                st.dataframe(df_corr.round(2), use_container_width=True)
                
            if correlation.highly_correlated_pairs:
                st.warning(f"⚠️ **Highly Correlated Pairs:** {correlation.correlation_warning}")
                
        # ----------------- 6. RISK LOG EVENTS -----------------
        st.markdown("---")
        st.subheader("📜 Risk Limits Incident Log")
        
        events = load_risk_events(limit=50, db_path=db_path)
        if not events:
            st.info("No risk incidents logged.")
        else:
            df_evts = pd.DataFrame([{
                "Timestamp": e.created_at,
                "Symbol": e.symbol,
                "Event Type": e.event_type,
                "Risk Status": e.risk_status,
                "Reason": e.reason
            } for e in events])
            st.dataframe(df_evts, use_container_width=True)
            
        # ----------------- 7. RISK SETTINGS EDITOR -----------------
        st.markdown("---")
        st.subheader("🔧 Global Risk Settings Settings")
        
        with st.form("settings_form"):
            col_set1, col_set2, col_set3 = st.columns(3)
            with col_set1:
                se_equity = st.number_input("Account Equity ($)", min_value=1.0, value=float(settings.account_equity), step=1000.0)
            with col_set2:
                se_risk = st.number_input("Risk Per Trade (Pct %)", min_value=0.1, max_value=10.0, value=float(settings.risk_per_trade_pct), step=0.1)
            with col_set3:
                se_daily = st.number_input("Max Daily Risk (Pct %)", min_value=0.1, max_value=50.0, value=float(settings.max_daily_risk_pct), step=0.5)
                
            col_set4, col_set5, col_set6 = st.columns(3)
            with col_set4:
                se_open = st.number_input("Max Open Risk (Pct %)", min_value=0.1, max_value=50.0, value=float(settings.max_total_open_risk_pct), step=0.5)
            with col_set5:
                se_concurrent = st.number_input("Max Concurrent Trades", min_value=1, max_value=50, value=int(settings.max_concurrent_trades), step=1)
            with col_set6:
                se_same_dir = st.number_input("Max Same Direction Trades", min_value=1, max_value=20, value=int(settings.max_same_direction_trades), step=1)
                
            col_set7, col_set8, col_set9 = st.columns(3)
            with col_set7:
                se_corr_thresh = st.number_input("Correlation Threshold", min_value=0.1, max_value=1.0, value=float(settings.correlation_threshold), step=0.05)
            with col_set8:
                se_corr_bars = st.number_input("Correlation Lookback Bars", min_value=10, max_value=500, value=int(settings.correlation_lookback_bars), step=5)
            with col_set9:
                se_corr_ttl = st.number_input("Correlation Cache TTL (Sec)", min_value=0, max_value=86400, value=int(settings.correlation_cache_ttl_seconds), step=60)
                
            col_set10, col_set11 = st.columns(2)
            with col_set10:
                se_def_mult = st.number_input("Default Multiplier", min_value=0.001, value=float(settings.default_contract_multiplier))
            with col_set11:
                se_def_pv = st.number_input("Default Point Value", min_value=0.001, value=float(settings.default_point_value))
                
            submit_settings = st.form_submit_button("Save Portfolio Risk Settings")
            if submit_settings:
                settings.account_equity = se_equity
                settings.risk_per_trade_pct = se_risk
                settings.max_daily_risk_pct = se_daily
                settings.max_total_open_risk_pct = se_open
                settings.max_concurrent_trades = se_concurrent
                settings.max_same_direction_trades = se_same_dir
                settings.correlation_threshold = se_corr_thresh
                settings.correlation_lookback_bars = se_corr_bars
                settings.correlation_cache_ttl_seconds = se_corr_ttl
                settings.default_contract_multiplier = se_def_mult
                settings.default_point_value = se_def_pv
                
                save_portfolio_settings(settings, db_path)
                st.success("Portfolio Risk Settings saved successfully!")
                st.rerun()
                
    except Exception as general_err:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการโหลดหน้าข้อมูลความเสี่ยงพอร์ต (Error: {str(general_err)})")
        logger.error(f"General error in render_portfolio_ui: {str(general_err)}")
