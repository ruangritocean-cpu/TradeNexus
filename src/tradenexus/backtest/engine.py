import pandas as pd
import numpy as np
import uuid
import logging
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk
from tradenexus.journal.outcome import evaluate_signal_outcome
from tradenexus.journal.repository import generate_signal_id
from tradenexus.indicators.volume import calculate_volume_indicators
from tradenexus.indicators.structure import calculate_smc_structures
from tradenexus.indicators.liquidity import calculate_liquidity_zones
from tradenexus.regime.classifier import classify_market_regime

logger = logging.getLogger(__name__)

def run_mtf_backtest(
    tf_dfs: dict,
    symbol: str,
    trigger_tf: str = "1h",
    rr_threshold: float = 1.5,
    max_bars_to_hold: int = 100,
    slippage_points: float = 0.0,
    commission_pct: float = 0.0
) -> dict:
    """
    Event-driven sequential Multi-Timeframe backtester with cost controls (slippage and commission).
    
    Processes trigger timeframe candles chronologically, aligning them
    with Daily, 4H, and 15m trend snapshots at each point in time.
    
    Strictly uses confirmed active SMC levels only (Support_Level/Resistance_Level).
    """
    # Create copies of dataframes to prevent mutating original inputs
    backtest_dfs = {}
    for tf in ["15m", "1h", "4h", "1d"]:
        if tf in tf_dfs and not tf_dfs[tf].empty:
            df_tf = tf_dfs[tf].copy()
            df_tf = calculate_volume_indicators(df_tf)
            df_tf = calculate_smc_structures(df_tf)
            df_tf = calculate_liquidity_zones(df_tf)
            
            # Run regime classification on a rolling look-back basis
            primary_regimes = []
            regime_scores = []
            regime_flags_list = []
            
            for idx in range(len(df_tf)):
                sub_df = df_tf.iloc[:idx+1]
                reg_res = classify_market_regime(sub_df)
                primary_regimes.append(reg_res["primary_regime"])
                regime_scores.append(reg_res["regime_score"])
                regime_flags_list.append(",".join(reg_res["flags"]))
                
            df_tf["primary_regime"] = primary_regimes
            df_tf["regime_score"] = regime_scores
            df_tf["regime_flags"] = regime_flags_list
            backtest_dfs[tf] = df_tf
            
    df_trigger = backtest_dfs.get(trigger_tf, pd.DataFrame())
    df_15m = backtest_dfs.get("15m", pd.DataFrame())
    df_1h = backtest_dfs.get("1h", pd.DataFrame())
    df_4h = backtest_dfs.get("4h", pd.DataFrame())
    df_1d = backtest_dfs.get("1d", pd.DataFrame())
    
    if df_trigger.empty or df_1d.empty or df_4h.empty:
        logger.warning("Empty timeframe dataframes provided for backtest.")
        return {"run_id": str(uuid.uuid4()), "signals": []}
        
    run_id = f"run_{int(pd.Timestamp.now().timestamp())}"
    signals = []
    
    # Start loop after warm-up period (min 100 bars)
    start_idx = 100
    if len(df_trigger) <= start_idx:
        start_idx = len(df_trigger) // 2
        
    for i in range(start_idx, len(df_trigger)):
        trigger_row = df_trigger.iloc[i]
        t_trigger = df_trigger.index[i]
        
        # Align other timeframes up to t_trigger to prevent look-ahead bias
        d_sub = df_1d.loc[df_1d.index <= t_trigger]
        f_sub = df_4h.loc[df_4h.index <= t_trigger]
        o_sub = df_1h.loc[df_1h.index <= t_trigger]
        m_sub = df_15m.loc[df_15m.index <= t_trigger]
        
        if d_sub.empty or f_sub.empty:
            continue
            
        daily_row = d_sub.iloc[-1]
        fourh_row = f_sub.iloc[-1]
        oneh_row = o_sub.iloc[-1] if not o_sub.empty else trigger_row
        fifteenm_row = m_sub.iloc[-1] if not m_sub.empty else trigger_row
        
        # 1. MTF Hierarchy trend alignment
        bias_1d = daily_row.get("CDC_Trend", "Neutral")
        setup_4h = fourh_row.get("CDC_Trend", "Neutral")
        trigger_1h = oneh_row.get("CDC_Trend", "Neutral")
        exec_15m = fifteenm_row.get("CDC_Trend", "Neutral")
        
        mtf_res = evaluate_mtf_hierarchy(bias_1d, setup_4h, trigger_1h, exec_15m)
        alignment_type = mtf_res["alignment_type"]
        
        # 2. Score evaluation on trigger row (includes volume & regime info)
        trigger_row_dict = trigger_row.to_dict()
        confluence_res = calculate_confluence_score(trigger_row_dict)
        dir_score = confluence_res["directional_score"]
        
        direction = "NEUTRAL"
        if dir_score >= 60:
            direction = "BUY"
        elif dir_score <= -60:
            direction = "SELL"
            
        if direction == "NEUTRAL":
            continue
            
        # 3. Risk veto checks
        support_val = trigger_row.get("Support_Level", 0.0)
        resistance_val = trigger_row.get("Resistance_Level", 0.0)
        atr_val = trigger_row.get("ATR", 0.0)
        
        risk_res = validate_trade_risk(
            price=trigger_row["Close"],
            decision=direction,
            support=support_val,
            resistance=resistance_val,
            atr=atr_val,
            rr_min=rr_threshold
        )
        
        # Re-compute quality score with calculated RR
        trigger_row_dict["RR_TP1"] = risk_res["RR_TP1"]
        confluence_res = calculate_confluence_score(trigger_row_dict)
        
        # 4. Preliminary Decision State Machine
        decision_state = "NO TRADE"
        if risk_res["Vetoed"]:
            decision_state = "NO TRADE"
        else:
            if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
                if confluence_res["confluence_score"] >= 70:
                    decision_state = "ENTRY TRIGGERED"
                else:
                    decision_state = "READY"
            else:
                decision_state = "WATCH"
                
        # 5. Apply Regime-Aware Decision Rules
        regime = trigger_row.get("primary_regime", "UNKNOWN")
        flags = trigger_row.get("regime_flags", "").split(",") if trigger_row.get("regime_flags", "") else []
        
        decision_state, regime_reasons, regime_warnings = apply_regime_decision_rules(
            decision_state=decision_state,
            primary_regime=regime,
            flags=flags,
            confluence_score=confluence_res["confluence_score"]
        )
        
        if decision_state == "ENTRY TRIGGERED":
            # 6. Apply slippage adjustments to entry, SL, and TP targets
            raw_entry = risk_res["Entry"]
            raw_sl = risk_res["StopLoss"]
            raw_tp1 = risk_res["TakeProfit1"]
            raw_tp2 = risk_res["TakeProfit2"]
            
            if direction == "BUY":
                entry = raw_entry + slippage_points
                sl = raw_sl - slippage_points
                tp1 = raw_tp1 - slippage_points
                tp2 = raw_tp2 - slippage_points
            else: # SELL
                entry = raw_entry - slippage_points
                sl = raw_sl + slippage_points
                tp1 = raw_tp1 + slippage_points
                tp2 = raw_tp2 + slippage_points
                
            # 7. Evaluate outcome on future historical data
            outcome_res = evaluate_signal_outcome(
                df=df_trigger,
                entry_time=t_trigger,
                direction=direction,
                entry=entry,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                max_bars=max_bars_to_hold
            )
            
            # 8. Calculate cost-adjusted realized R (commission)
            risk_points = abs(entry - sl)
            status = outcome_res["status"]
            bars = outcome_res["bars_to_outcome"]
            outcome_time = outcome_res["outcome_time"]
            
            # Determine actual exit price based on status
            exit_price = entry
            if status == "SL_HIT":
                exit_price = sl
            elif status == "TP1_HIT":
                exit_price = tp1
            elif status == "TP2_HIT":
                exit_price = tp2
            elif status == "EXPIRED":
                future_df = df_trigger.loc[df_trigger.index > t_trigger].head(max_bars_to_hold)
                if not future_df.empty:
                    exit_price = future_df.iloc[-1]["Close"]
                    
            costs_points = (entry + exit_price) * (commission_pct / 100.0)
            
            if risk_points > 0:
                if direction == "BUY":
                    net_return = (exit_price - entry) - costs_points
                else:
                    net_return = (entry - exit_price) - costs_points
                realized_r = net_return / risk_points
            else:
                realized_r = 0.0
                
            sig_id = generate_signal_id(
                symbol=symbol,
                timeframe=trigger_tf,
                candle_close_time=t_trigger.isoformat(),
                decision_state=decision_state,
                direction=direction,
                entry=entry,
                sl=sl,
                tp1=tp1
            )
            
            signals.append({
                "signal_id": sig_id,
                "symbol": symbol,
                "timeframe": trigger_tf,
                "candle_close_time": t_trigger.isoformat(),
                "decision_state": decision_state,
                "direction": direction,
                "alignment_type": alignment_type,
                "entry": entry,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "rr_tp1": ((tp1 - entry) / risk_points) if risk_points > 0 and direction == "BUY" else (((entry - tp1) / risk_points) if risk_points > 0 else 0.0),
                "rr_tp2": ((tp2 - entry) / risk_points) if risk_points > 0 and direction == "BUY" else (((entry - tp2) / risk_points) if risk_points > 0 else 0.0),
                "confluence_score": confluence_res["confluence_score"],
                "directional_score": dir_score,
                "quality_score": confluence_res["quality_score"],
                "market_bias": bias_1d,
                "setup_direction": setup_4h,
                "trigger_direction": trigger_1h,
                "execution_direction": exec_15m,
                "smc_support_source": trigger_row.get("Support_Source", "FALLBACK"),
                "smc_resistance_source": trigger_row.get("Resistance_Source", "FALLBACK"),
                "data_quality_valid": 1,
                "is_actionable": 1,
                "outcome_status": status,
                "outcome_time": outcome_time,
                "bars_to_outcome": bars,
                "realized_r_multiple": realized_r,
                "reasons": confluence_res["reasons"] + mtf_res["reasons"] + regime_reasons,
                "warnings": confluence_res["warnings"] + mtf_res["warnings"] + regime_warnings,
                "primary_regime": regime,
                "regime_flags": trigger_row.get("regime_flags", ""),
                "regime_score": trigger_row.get("regime_score", 0.0),
                "volume_confirmation": trigger_row.get("Volume_Confirmation", "NEUTRAL"),
                "vwap_alignment": "BULLISH" if trigger_row.get("Close") > trigger_row.get("VWAP", trigger_row.get("Close")) else "BEARISH",
                "bos_present": trigger_row.get("BOS_Present", 0),
                "choch_present": trigger_row.get("CHOCH_Present", 0),
                "fvg_present": trigger_row.get("FVG_Present", 0),
                "liquidity_sweep_present": trigger_row.get("Liquidity_Sweep", 0)
            })
            
    return {
        "run_id": run_id,
        "signals": signals
    }
