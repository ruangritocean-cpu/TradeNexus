import datetime
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import uuid
import json

# Data and Indicators (Pipelines & Cache & Providers)
from tradenexus.data.providers import fetch_ohlcv_data
from tradenexus.data.resampling import resample_timeframe
from tradenexus.pipeline.indicator_pipeline import calculate_all_indicators

# Rules & Vetoes
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk
from tradenexus.journal.guard import is_candle_closed
from tradenexus.journal.repository import insert_signal, generate_signal_id
from tradenexus.journal.models import Signal
from tradenexus.alerts.dispatcher import dispatch_alert
from tradenexus.scanner.watchlist import load_watchlist
from tradenexus.scanner.scan_models import ScanResult, ScanRun
from tradenexus.scanner.scan_repository import insert_scan_run

# Portfolio Integration
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings, load_symbol_profile, insert_risk_event
from tradenexus.portfolio.position_sizing import calculate_position_size
from tradenexus.portfolio.exposure import calculate_portfolio_exposure
from tradenexus.portfolio.correlation import calculate_returns_correlation
from tradenexus.portfolio.limits import check_portfolio_risk_limits
from tradenexus.portfolio.risk_models import PortfolioRiskEvent

logger = logging.getLogger(__name__)

def run_watchlist_scan(
    db_path: str = None,
    watchlist_path: str = None,
    discord_webhook: str = "",
    tg_bot_token: str = "",
    tg_chat_id: str = "",
    max_symbols: int = 20,
    force_all_candles: bool = False
) -> dict:
    """
    Sequentially scans enabled symbols in the watchlist.
    Integrates Portfolio Risk management (limits, sizing, event logs) and shared pipelines.
    """
    # Precision UUID run ID
    scan_run_id = f"scan_{uuid.uuid4().hex[:8]}"
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Load settings and current exposure
    p_settings = load_portfolio_settings(db_path)
    p_exposure = calculate_portfolio_exposure(db_path, p_settings)
    
    watchlist = load_watchlist(watchlist_path)
    enabled_items = [item for item in watchlist if item.get("enabled", True)]
    
    # Cap by max symbols
    enabled_items = enabled_items[:max_symbols]
    
    # Compute correlation
    enabled_syms = [x["symbol"] for x in enabled_items]
    p_correlation = calculate_returns_correlation(
        symbols=enabled_syms,
        lookback_bars=p_settings.correlation_lookback_bars,
        correlation_threshold=p_settings.correlation_threshold,
        cache_ttl_seconds=p_settings.correlation_cache_ttl_seconds
    )
    
    total_symbols = len(enabled_items)
    success_count = 0
    warning_count = 0
    error_count = 0
    skipped_count = 0
    
    results = []
    
    for item in enabled_items:
        symbol = item["symbol"]
        pref_tfs = item.get("preferred_timeframes", ["1h", "4h"])
        alert_ready = item.get("alert_ready_enabled", False)
        alert_entry = item.get("alert_entry_enabled", True)
        min_conf = item.get("min_confluence_score", 70.0)
        min_rr = item.get("min_rr", 1.5)
        
        symbol_has_error = False
        symbol_has_warning = False
        
        # 1. Fetch and resample MTF data using fetch_ohlcv_result
        try:
            from tradenexus.data.providers import fetch_ohlcv_result
            
            asset_class = "CRYPTO" if ("BTC" in symbol or "ETH" in symbol) else "EQUITIES"
            
            res_15m = fetch_ohlcv_result(symbol, interval="15m", asset_class=asset_class)
            res_1h = fetch_ohlcv_result(symbol, interval="1h", asset_class=asset_class)
            res_1d = fetch_ohlcv_result(symbol, interval="1d", asset_class=asset_class)
            
            if (res_15m.data_quality_status == "INVALID" or 
                res_1h.data_quality_status == "INVALID" or 
                res_1d.data_quality_status == "INVALID"):
                all_errors = res_15m.errors + res_1h.errors + res_1d.errors
                raise ValueError("Data Quality Check is INVALID: " + "; ".join(all_errors))
                
            df_15m = res_15m.df.copy()
            df_1h = res_1h.df.copy()
            df_1d = res_1d.df.copy()
            
            # Map Capitalized columns for indicator calculation compatibility
            for df_temp in [df_15m, df_1h, df_1d]:
                df_temp["Open"] = df_temp["open"]
                df_temp["High"] = df_temp["high"]
                df_temp["Low"] = df_temp["low"]
                df_temp["Close"] = df_temp["close"]
                df_temp["Volume"] = df_temp["volume"]
                
            df_4h = resample_timeframe(df_1h, "4h")
            if not df_4h.empty:
                df_4h["open"] = df_4h["Open"]
                df_4h["high"] = df_4h["High"]
                df_4h["low"] = df_4h["Low"]
                df_4h["close"] = df_4h["Close"]
                df_4h["volume"] = df_4h["Volume"]
                df_4h["timestamp"] = df_4h.index.map(lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))
                df_4h["provider"] = res_1h.provider_used
                df_4h["symbol"] = symbol
                df_4h["interval"] = "4h"
            
            tf_dfs = {
                "15m": df_15m,
                "1h": df_1h,
                "4h": df_4h,
                "1d": df_1d
            }
            
            tf_results = {
                "15m": res_15m,
                "1h": res_1h,
                "1d": res_1d,
                "4h": res_1h
            }
            
            # Compute indicators for all timeframes via shared indicator pipeline
            for tf in ["15m", "1h", "4h", "1d"]:
                tf_dfs[tf] = calculate_all_indicators(tf_dfs[tf])
                
        except Exception as ex:
            error_count += 1
            results.append(ScanResult(
                scan_run_id=scan_run_id,
                symbol=symbol,
                timeframe="ALL",
                scan_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                symbol_status="ERROR",
                decision_state="UNKNOWN",
                direction="NEUTRAL",
                alignment_type="CONFLICTED",
                confluence_score=0.0,
                rr_tp1=0.0,
                primary_regime="UNKNOWN",
                regime_flags_json="[]",
                data_quality_status="INVALID",
                alert_status="SKIPPED_ERROR",
                journal_status="SKIPPED_ERROR",
                reasons_json="[]",
                warnings_json="[]",
                error_message=str(ex),
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                provider_used="unknown",
                fallback_used=0,
                data_quality_warnings_json="[]",
                data_quality_errors_json="[]",
                latest_candle_time=None,
                bars_available=0
            ))
            continue
            
        # Scan preferred timeframes
        for tf in pref_tfs:
            res_tf = tf_results.get(tf)
            df_tf = tf_dfs.get(tf, pd.DataFrame())
            if df_tf.empty or len(df_tf) < 2:
                skipped_count += 1
                results.append(ScanResult(
                    scan_run_id=scan_run_id,
                    symbol=symbol,
                    timeframe=tf,
                    scan_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    symbol_status="SKIPPED_EMPTY_DATA",
                    decision_state="NO TRADE",
                    direction="NEUTRAL",
                    alignment_type="CONFLICTED",
                    confluence_score=0.0,
                    rr_tp1=0.0,
                    primary_regime="UNKNOWN",
                    regime_flags_json="[]",
                    data_quality_status="INVALID",
                    alert_status="SKIPPED_EMPTY",
                    journal_status="SKIPPED_EMPTY",
                    reasons_json="[]",
                    warnings_json="[]",
                    error_message="Historical data too short.",
                    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    provider_used=res_tf.provider_used if res_tf else "unknown",
                    fallback_used=res_tf.fallback_used if res_tf else 0,
                    data_quality_warnings_json=json.dumps(res_tf.warnings) if res_tf else "[]",
                    data_quality_errors_json=json.dumps(res_tf.errors) if res_tf else "[]",
                    latest_candle_time=res_tf.latest_candle_time if res_tf else None,
                    bars_available=res_tf.bars_available if res_tf else 0
                ))
                continue
                
            closed_row = df_tf.iloc[-2]
            closed_time = df_tf.index[-2]
            
            # Guard closed candle check
            is_closed = is_candle_closed(closed_time, tf, mode="live") or force_all_candles
            if not is_closed:
                skipped_count += 1
                results.append(ScanResult(
                    scan_run_id=scan_run_id,
                    symbol=symbol,
                    timeframe=tf,
                    scan_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    symbol_status="SKIPPED_OPEN_CANDLE",
                    decision_state="NO TRADE",
                    direction="NEUTRAL",
                    alignment_type="CONFLICTED",
                    confluence_score=0.0,
                    rr_tp1=0.0,
                    primary_regime="UNKNOWN",
                    regime_flags_json="[]",
                    data_quality_status="VALID",
                    alert_status="SKIPPED_OPEN",
                    journal_status="SKIPPED_OPEN",
                    reasons_json="[]",
                    warnings_json="[]",
                    error_message="Candle still open.",
                    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    provider_used=res_tf.provider_used if res_tf else "unknown",
                    fallback_used=res_tf.fallback_used if res_tf else 0,
                    data_quality_warnings_json=json.dumps(res_tf.warnings) if res_tf else "[]",
                    data_quality_errors_json=json.dumps(res_tf.errors) if res_tf else "[]",
                    latest_candle_time=res_tf.latest_candle_time if res_tf else None,
                    bars_available=res_tf.bars_available if res_tf else 0
                ))
                continue
                
            # Align higher/lower timeframes to closed_time to prevent look-ahead bias
            d_sub = tf_dfs["1d"].loc[tf_dfs["1d"].index <= closed_time]
            f_sub = tf_dfs["4h"].loc[tf_dfs["4h"].index <= closed_time]
            o_sub = tf_dfs["1h"].loc[tf_dfs["1h"].index <= closed_time]
            m_sub = tf_dfs["15m"].loc[tf_dfs["15m"].index <= closed_time]
            
            bias_1d = d_sub.iloc[-1].get("CDC_Trend", "Neutral") if not d_sub.empty else "Neutral"
            setup_4h = f_sub.iloc[-1].get("CDC_Trend", "Neutral") if not f_sub.empty else "Neutral"
            trigger_1h = o_sub.iloc[-1].get("CDC_Trend", "Neutral") if not o_sub.empty else "Neutral"
            exec_15m = m_sub.iloc[-1].get("CDC_Trend", "Neutral") if not m_sub.empty else "Neutral"
            
            mtf_res = evaluate_mtf_hierarchy(bias_1d, setup_4h, trigger_1h, exec_15m)
            alignment_type = mtf_res["alignment_type"]
            
            # Confluence Score calculation
            closed_row_dict = closed_row.to_dict()
            scoring_res = calculate_confluence_score(closed_row_dict)
            dir_score = scoring_res["directional_score"]
            
            direction = "NEUTRAL"
            if dir_score >= 60:
                direction = "BUY"
            elif dir_score <= -60:
                direction = "SELL"
                
            c_state = "NO TRADE"
            risk_res = {"Vetoed": True, "Entry": 0.0, "StopLoss": 0.0, "TakeProfit1": 0.0, "TakeProfit2": 0.0, "RR_TP1": 0.0, "RR_TP2": 0.0, "R_Vetoed": 1}
            
            if direction != "NEUTRAL":
                support_val = closed_row.get("Support_Level", 0.0)
                resistance_val = closed_row.get("Resistance_Level", 0.0)
                atr_val = closed_row.get("ATR", 0.0)
                
                risk_res = validate_trade_risk(
                    price=closed_row["Close"],
                    decision=direction,
                    support=support_val,
                    resistance=resistance_val,
                    atr=atr_val,
                    rr_min=min_rr
                )
                
                closed_row_dict["RR_TP1"] = risk_res["RR_TP1"]
                scoring_res = calculate_confluence_score(closed_row_dict)
                
                if not risk_res["Vetoed"]:
                    if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
                        if scoring_res["confluence_score"] >= 70:
                            c_state = "ENTRY TRIGGERED"
                        else:
                            c_state = "READY"
                    else:
                        c_state = "WATCH"
                else:
                    c_state = "NO TRADE"
                    
            # Apply Regime override rules
            regime = closed_row.get("primary_regime", "UNKNOWN")
            flags = closed_row.get("regime_flags", "").split(",") if closed_row.get("regime_flags", "") else []
            c_state, regime_reasons, regime_warnings = apply_regime_decision_rules(
                decision_state=c_state,
                primary_regime=regime,
                flags=flags,
                confluence_score=scoring_res["confluence_score"]
            )
            
            # Check warnings
            warnings_list = scoring_res["warnings"] + mtf_res["warnings"] + regime_warnings
            
            # Apply Playbook Rule Engine
            pb_status = "PASS"
            if c_state in ["READY", "ENTRY TRIGGERED"]:
                from tradenexus.playbook.playbook_repository import get_active_playbook
                from tradenexus.playbook.rule_engine import evaluate_playbook_rules
                
                playbook = get_active_playbook(db_path)
                pb_status, pb_passed, pb_warnings, pb_violations = evaluate_playbook_rules(
                    playbook=playbook,
                    symbol=symbol,
                    timeframe=tf,
                    setup_type=alignment_type,
                    confluence_score=scoring_res["confluence_score"],
                    rr=risk_res.get("RR_TP1", 0.0),
                    market_regime=regime,
                    db_path=db_path
                )
                
                if pb_status == "BLOCKED":
                    warnings_list.extend(pb_violations)
                elif pb_status == "WARNING":
                    warnings_list.extend(pb_warnings)
                    
            if warnings_list:
                symbol_has_warning = True
                
            # Process Database Journaling
            journal_status = "SKIPPED_NO_TRADE"
            sig_id = None
            
            is_actionable = 1 if (c_state in ["READY", "ENTRY TRIGGERED"] and pb_status != "BLOCKED") else 0
            
            # Candidate Sizing Calculation
            pos_size_units = 0.0
            candidate_risk_amount = 0.0
            candidate_risk_pct = 0.0
            
            if is_actionable:
                sig_id = generate_signal_id(
                    symbol=symbol,
                    timeframe=tf,
                    candle_close_time=closed_time.isoformat(),
                    decision_state=c_state,
                    direction=direction,
                    entry=risk_res["Entry"],
                    sl=risk_res["StopLoss"],
                    tp1=risk_res["TakeProfit1"]
                )
                
                # Load symbol profile and perform sizing calculations
                sym_profile = load_symbol_profile(symbol, db_path)
                if sym_profile is None:
                    from tradenexus.portfolio.risk_models import SymbolRiskProfile
                    sym_profile = SymbolRiskProfile(
                        symbol=symbol,
                        asset_class="CRYPTO",
                        point_value=1.0,
                        contract_multiplier=1.0,
                        min_position_size=0.01,
                        position_step=0.01,
                        currency="USD",
                        updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    )
                sizing_res = calculate_position_size(
                    account_equity=p_settings.account_equity,
                    risk_per_trade_pct=p_settings.risk_per_trade_pct,
                    entry=risk_res["Entry"],
                    stop_loss=risk_res["StopLoss"],
                    direction=direction,
                    point_value=sym_profile.point_value,
                    contract_multiplier=sym_profile.contract_multiplier,
                    min_position_size=sym_profile.min_position_size,
                    position_step=sym_profile.position_step,
                    tp1=risk_res["TakeProfit1"],
                    tp2=risk_res["TakeProfit2"]
                )
                pos_size_units = sizing_res.position_size_units
                candidate_risk_amount = sizing_res.risk_amount
                candidate_risk_pct = (sizing_res.risk_amount / p_settings.account_equity * 100.0) if p_settings.account_equity > 0 else 0.0
                
                db_signal = Signal(
                    signal_id=sig_id,
                    symbol=symbol,
                    timeframe=tf,
                    candle_close_time=closed_time.isoformat(),
                    decision_state=c_state,
                    direction=direction,
                    alignment_type=alignment_type,
                    entry=risk_res["Entry"],
                    sl=risk_res["StopLoss"],
                    tp1=risk_res["TakeProfit1"],
                    tp2=risk_res["TakeProfit2"],
                    rr_tp1=risk_res["RR_TP1"],
                    rr_tp2=risk_res["RR_TP2"],
                    confluence_score=scoring_res["confluence_score"],
                    directional_score=dir_score,
                    quality_score=scoring_res["quality_score"],
                    market_bias=bias_1d,
                    setup_direction=setup_4h,
                    trigger_direction=trigger_1h,
                    execution_direction=exec_15m,
                    smc_support_source=closed_row.get("Support_Source", "FALLBACK"),
                    smc_resistance_source=closed_row.get("Resistance_Source", "FALLBACK"),
                    data_quality_valid=1,
                    is_actionable=is_actionable,
                    reasons=scoring_res["reasons"] + mtf_res["reasons"] + regime_reasons,
                    warnings=warnings_list,
                    primary_regime=regime,
                    regime_score=closed_row.get("regime_score", 0.0),
                    regime_flags=closed_row.get("regime_flags", ""),
                    volume_confirmation=closed_row.get("Volume_Confirmation", "NEUTRAL"),
                    vwap_alignment="BULLISH" if closed_row["Close"] > closed_row.get("VWAP", closed_row["Close"]) else "BEARISH",
                    bos_present=closed_row.get("BOS_Present", 0),
                    choch_present=closed_row.get("CHOCH_Present", 0),
                    fvg_present=closed_row.get("FVG_Present", 0),
                    liquidity_sweep_present=closed_row.get("Liquidity_Sweep", 0)
                )
                
                # Try inserting signal (blocks duplicates internally via unique key)
                inserted = insert_signal(db_signal, db_path)
                journal_status = "SAVED" if inserted else "SKIPPED_DUPLICATE"
                
            # Process Alerting Filters
            alert_status = "SKIPPED_FILTER"
            portfolio_risk_status = "OK"
            block_reason = ""
            
            # Check Playbook blocking first
            if pb_status == "BLOCKED":
                alert_status = "BLOCKED_BY_PLAYBOOK"
            
            # Run Portfolio Risk check if setup is actionable
            elif is_actionable:
                limits_res = check_portfolio_risk_limits(
                    settings=p_settings,
                    exposure=p_exposure,
                    correlation=p_correlation,
                    candidate_direction=direction
                )
                
                if limits_res.risk_status == "BLOCKED":
                    portfolio_risk_status = "BLOCKED"
                    block_reason = ", ".join(limits_res.reasons)
                    alert_status = "BLOCKED_BY_PORTFOLIO_RISK"
                    
                    # Record risk event log
                    evt_id = f"evt_{uuid.uuid4().hex[:8]}"
                    event = PortfolioRiskEvent(
                        event_id=evt_id,
                        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        signal_id=sig_id,
                        trade_id=None,
                        symbol=symbol,
                        event_type="ALERT_BLOCKED",
                        risk_status="BLOCKED",
                        reason=block_reason,
                        details_json=json.dumps({
                            "timeframe": tf,
                            "confluence_score": scoring_res["confluence_score"]
                        })
                    )
                    insert_risk_event(event, db_path)
                    
            # Check alert settings
            allowed_alert_state = False
            if c_state == "ENTRY TRIGGERED" and alert_entry:
                allowed_alert_state = True
            elif c_state == "READY" and alert_ready:
                allowed_alert_state = True
                
            # Check if all filtering logic passes
            if (
                item.get("alert_enabled", True)
                and allowed_alert_state
                and scoring_res["confluence_score"] >= min_conf
                and risk_res["R_Vetoed"] == 0  # not vetoed
                and "LOW_LIQUIDITY" not in flags
                and portfolio_risk_status != "BLOCKED"
                and pb_status != "BLOCKED"
            ):
                strategy_payload = {
                    "Decision": c_state,
                    "Direction": direction,
                    "AlignmentType": alignment_type,
                    "Entry": risk_res["Entry"],
                    "StopLoss": risk_res["StopLoss"],
                    "TakeProfit1": risk_res["TakeProfit1"],
                    "TakeProfit2": risk_res["TakeProfit2"],
                    "RR_TP1": risk_res["RR_TP1"],
                    "ConfluenceScore": scoring_res["confluence_score"],
                    "Regime": regime,
                    "Reasons": scoring_res["reasons"] + mtf_res["reasons"] + regime_reasons,
                    "Warnings": warnings_list
                }
                
                # Dispatch alerts (will dedup via alert_log table check internally)
                dispatch_res = dispatch_alert(
                    signal_id=sig_id or f"manual_{uuid.uuid4().hex[:8]}",
                    ticker=symbol,
                    timeframe=tf,
                    strategy=strategy_payload,
                    discord_webhook_url=discord_webhook,
                    tg_bot_token=tg_bot_token,
                    tg_chat_id=tg_chat_id,
                    db_path=db_path
                )
                
                d_status = dispatch_res.get("discord", "NOT_CONFIGURED")
                t_status = dispatch_res.get("telegram", "NOT_CONFIGURED")
                
                if d_status == "NOT_CONFIGURED" and t_status == "NOT_CONFIGURED":
                    alert_status = "SKIPPED_NO_PROVIDER"
                elif d_status == "SENT" and t_status == "SENT":
                    alert_status = "SENT"
                elif d_status in ["SENT", "SKIPPED_DUPLICATE"] and t_status in ["SENT", "SKIPPED_DUPLICATE"]:
                    if d_status == "SKIPPED_DUPLICATE" or t_status == "SKIPPED_DUPLICATE":
                        alert_status = "SKIPPED_DUPLICATE"
                    else:
                        alert_status = "SENT"
                elif d_status == "SENT" or t_status == "SENT":
                    alert_status = "PARTIAL_SENT"
                elif d_status == "FAILED" or t_status == "FAILED":
                    alert_status = "FAILED_PROVIDER"
                else:
                    alert_status = "SKIPPED_DUPLICATE"
                
            results.append(ScanResult(
                scan_run_id=scan_run_id,
                signal_id=sig_id,
                symbol=symbol,
                timeframe=tf,
                scan_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                symbol_status="WARNING" if symbol_has_warning else "SUCCESS",
                decision_state=c_state,
                direction=direction,
                alignment_type=alignment_type,
                confluence_score=scoring_res["confluence_score"],
                rr_tp1=risk_res["RR_TP1"],
                primary_regime=regime,
                regime_flags_json=json.dumps(flags),
                data_quality_status=res_tf.data_quality_status if res_tf else "VALID",
                alert_status=alert_status,
                journal_status=journal_status,
                reasons_json=json.dumps(scoring_res["reasons"] + mtf_res["reasons"] + regime_reasons),
                warnings_json=json.dumps(warnings_list),
                error_message=block_reason,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                position_size_units=pos_size_units,
                candidate_risk_amount=candidate_risk_amount,
                candidate_risk_pct=candidate_risk_pct,
                provider_used=res_tf.provider_used if res_tf else "unknown",
                fallback_used=res_tf.fallback_used if res_tf else 0,
                data_quality_warnings_json=json.dumps(res_tf.warnings) if res_tf else "[]",
                data_quality_errors_json=json.dumps(res_tf.errors) if res_tf else "[]",
                latest_candle_time=res_tf.latest_candle_time if res_tf else None,
                bars_available=res_tf.bars_available if res_tf else 0
            ))
            
        if symbol_has_error:
            error_count += 1
        elif symbol_has_warning:
            warning_count += 1
        else:
            success_count += 1
            
    # Calculate Run status
    run_status = "COMPLETED"
    if error_count == total_symbols and total_symbols > 0:
        run_status = "FAILED"
    elif error_count > 0:
        run_status = "PARTIAL_SUCCESS"
        
    finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Save Scan Run to DB
    run_summary = ScanRun(
        scan_run_id=scan_run_id,
        started_at=started_at,
        finished_at=finished_at,
        status=run_status,
        total_symbols=total_symbols,
        success_count=success_count,
        warning_count=warning_count,
        error_count=error_count,
        skipped_count=skipped_count,
        config_json=json.dumps({
            "max_symbols": max_symbols,
            "force_all_candles": force_all_candles
        })
    )
    
    insert_scan_run(run_summary, db_path)
    
    # Save individual scan results
    from tradenexus.scanner.scan_repository import insert_scan_result
    for r in results:
        insert_scan_result(r, db_path)
        
    return {
        "scan_run_id": scan_run_id,
        "status": run_status,
        "started_at": started_at,
        "finished_at": finished_at,
        "results": results
    }
