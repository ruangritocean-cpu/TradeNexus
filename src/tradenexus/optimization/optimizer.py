import time
import uuid
import datetime
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk
from tradenexus.journal.outcome import evaluate_signal_outcome
from tradenexus.optimization.parameter_grid import generate_parameter_grid
from tradenexus.optimization.walk_forward import split_walk_forward_windows
from tradenexus.optimization.robustness import calculate_robustness_score
from tradenexus.optimization.optimization_repository import (
    save_optimization_run,
    update_optimization_run_status,
    save_optimization_result,
    save_parameter_recommendation
)
from tradenexus.indicators.volume import calculate_volume_indicators
from tradenexus.indicators.structure import calculate_smc_structures
from tradenexus.indicators.liquidity import calculate_liquidity_zones
from tradenexus.regime.classifier import classify_market_regime

logger = logging.getLogger(__name__)

def run_sandbox_backtest(
    tf_dfs: Dict[str, pd.DataFrame],
    symbol: str,
    trigger_tf: str,
    params: Dict[str, Any],
    start_idx_val: int = 100,
    slippage_points: float = 0.0,
    commission_pct: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Runs a sandboxed event-driven backtest simulation for a single parameter set.
    """
    df_trigger = tf_dfs.get(trigger_tf, pd.DataFrame())
    df_15m = tf_dfs.get("15m", pd.DataFrame())
    df_1h = tf_dfs.get("1h", pd.DataFrame())
    df_4h = tf_dfs.get("4h", pd.DataFrame())
    df_1d = tf_dfs.get("1d", pd.DataFrame())
    
    if df_trigger.empty or df_1d.empty or df_4h.empty:
        return []
        
    conf_thresh = params.get("confluence_threshold", 70.0)
    rr_min = params.get("rr_threshold", 1.5)
    adx_thresh = params.get("adx_threshold", 25.0)
    squeeze_block = params.get("squeeze_block_enabled", True)
    sideways_block = params.get("sideways_block_enabled", True)
    min_regime_sc = params.get("min_regime_score", 60.0)
    allow_counter = params.get("allow_counter_trend_scalp", True)
    max_bars = params.get("max_bars_to_hold", 24)
    
    trades = []
    
    start_idx = start_idx_val
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
        
        # 1. MTF CDC Trend
        bias_1d = daily_row.get("CDC_Trend", "Neutral")
        setup_4h = fourh_row.get("CDC_Trend", "Neutral")
        trigger_1h = oneh_row.get("CDC_Trend", "Neutral")
        exec_15m = fifteenm_row.get("CDC_Trend", "Neutral")
        
        mtf_res = evaluate_mtf_hierarchy(bias_1d, setup_4h, trigger_1h, exec_15m)
        alignment_type = mtf_res["alignment_type"]
        
        if not allow_counter and alignment_type == "COUNTER_TREND_SCALP":
            continue
            
        # 2. Confluence Evaluation
        trigger_row_dict = trigger_row.to_dict()
        adx_val = trigger_row_dict.get("ADX", 20.0)
        
        confluence_res = calculate_confluence_score(trigger_row_dict)
        q_score = confluence_res["quality_score"]
        
        # Custom ADX penalty if below adx_threshold
        if adx_val < adx_thresh and adx_val >= 25.0:
            q_score -= 10.0
            
        confluence_score = max(0.0, min(100.0, (confluence_res["directional_score"] * 0.5) + (q_score * 0.5)))
        
        # 3. Regime Score filter
        regime = trigger_row.get("primary_regime", "UNKNOWN")
        regime_score = trigger_row.get("regime_score", 50.0)
        if regime_score < min_regime_sc:
            continue
            
        direction = "NEUTRAL"
        if confluence_res["directional_score"] >= 60:
            direction = "BUY"
        elif confluence_res["directional_score"] <= -60:
            direction = "SELL"
            
        if direction == "NEUTRAL":
            continue
            
        # 4. Risk Veto checks
        support_val = trigger_row.get("Support_Level", 0.0)
        resistance_val = trigger_row.get("Resistance_Level", 0.0)
        atr_val = trigger_row.get("ATR", 0.0)
        
        risk_res = validate_trade_risk(
            price=trigger_row["Close"],
            decision=direction,
            support=support_val,
            resistance=resistance_val,
            atr=atr_val,
            rr_min=rr_min
        )
        
        # 5. Preliminary State
        decision_state = "NO TRADE"
        if risk_res["Vetoed"]:
            decision_state = "NO TRADE"
        else:
            if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
                if confluence_score >= conf_thresh:
                    decision_state = "ENTRY TRIGGERED"
                else:
                    decision_state = "READY"
            else:
                decision_state = "WATCH"
                
        # Squeeze/Sideways Overrides
        if squeeze_block and regime == "SQUEEZE" and decision_state == "ENTRY TRIGGERED":
            decision_state = "WATCH"
        if sideways_block and regime == "SIDEWAYS" and decision_state == "ENTRY TRIGGERED" and confluence_score < 80.0:
            decision_state = "WATCH"
            
        if decision_state == "ENTRY TRIGGERED":
            # Apply slippage
            raw_entry = risk_res["Entry"]
            raw_sl = risk_res["StopLoss"]
            raw_tp1 = risk_res["TakeProfit1"]
            raw_tp2 = risk_res["TakeProfit2"]
            
            if direction == "BUY":
                entry = raw_entry + slippage_points
                sl = raw_sl - slippage_points
                tp1 = raw_tp1 - slippage_points
                tp2 = raw_tp2 - slippage_points
            else:
                entry = raw_entry - slippage_points
                sl = raw_sl + slippage_points
                tp1 = raw_tp1 + slippage_points
                tp2 = raw_tp2 + slippage_points
                
            # Evaluate outcome on future historical data
            outcome_res = evaluate_signal_outcome(
                df=df_trigger,
                entry_time=t_trigger,
                direction=direction,
                entry=entry,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                max_bars=max_bars
            )
            
            # Apply commission
            status = outcome_res["status"]
            bars = outcome_res["bars_to_outcome"]
            exit_price = entry
            if status == "SL_HIT":
                exit_price = sl
            elif status == "TP1_HIT":
                exit_price = tp1
            elif status == "TP2_HIT":
                exit_price = tp2
                
            cost_factor = (entry + exit_price) * commission_pct
            raw_r = outcome_res["realized_r_multiple"]
            
            risk_points = abs(entry - sl)
            net_r = raw_r - (cost_factor / risk_points) if risk_points > 0 else raw_r
            
            trades.append({
                "status": status,
                "realized_r_multiple": net_r,
                "bars_to_outcome": bars
            })
            
    return trades

def calculate_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates trade history into core performance metrics.
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "profit_factor": 1.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0
        }
        
    wins = [t for t in trades if t["realized_r_multiple"] > 0]
    losses = [t for t in trades if t["realized_r_multiple"] <= 0]
    
    total_trades = len(trades)
    win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0.0
    
    gross_profits = sum([t["realized_r_multiple"] for t in wins])
    gross_losses = abs(sum([t["realized_r_multiple"] for t in losses]))
    
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
    expectancy = sum([t["realized_r_multiple"] for t in trades]) / total_trades if total_trades > 0 else 0.0
    
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t["realized_r_multiple"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            
    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_drawdown": max_dd,
        "total_trades": total_trades
    }

def run_walk_forward_optimization(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    train_window_bars: int,
    test_window_bars: int,
    step_bars: int,
    ranges: Dict[str, List[Any]] = None,
    max_combinations: int = 100,
    max_runtime_seconds: float = 300.0,
    final_holdout_bars: int = 0,
    sampling_seed: int = 42,
    slippage_points: float = 0.0,
    commission_pct: float = 0.0,
    db_path: str = None,
    progress_cb = None
) -> str:
    """
    Coordinates Walk-Forward Grid Search Optimization with sandboxing, cost-aware logic,
    reproducibility settings, holdout isolation, and strict runtime limit guards.
    """
    run_id = f"opt_{int(time.time())}"
    start_time = time.time()
    
    # 1. Initialize data frames from cache or fetch providers
    from tradenexus.data.providers import fetch_ohlcv_data
    from tradenexus.data.resampling import resample_timeframe
    
    config_dict = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": start_date,
        "end_date": end_date,
        "train_window_bars": train_window_bars,
        "test_window_bars": test_window_bars,
        "step_bars": step_bars,
        "final_holdout_bars": final_holdout_bars,
        "max_runtime_seconds": max_runtime_seconds,
        "slippage_points": slippage_points,
        "commission_pct": commission_pct
    }
    
    # Generate grid
    combos, grid_meta = generate_parameter_grid(ranges, max_combinations, sampling_seed)
    
    save_optimization_run(
        run_id=run_id,
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        train_window_bars=train_window_bars,
        test_window_bars=test_window_bars,
        step_bars=step_bars,
        max_combinations=max_combinations,
        status="RUNNING",
        config_dict=config_dict,
        sampling_seed=sampling_seed,
        sampling_method=grid_meta["grid_sampling_method"],
        total_combinations=grid_meta["grid_total_combinations"],
        evaluated_combinations=grid_meta["grid_evaluated_combinations"],
        db_path=db_path
    )
    
    try:
        # Load and pre-calculate indicators on raw timeframes once
        tf_dfs = {}
        for tf in ["15m", "1h", "4h", "1d"]:
            df_raw, warn_msg = fetch_ohlcv_data(symbol, tf)
            if not df_raw.empty:
                df_tf = calculate_volume_indicators(df_raw)
                df_tf = calculate_smc_structures(df_tf)
                df_tf = calculate_liquidity_zones(df_tf)
                
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
                tf_dfs[tf] = df_tf
                
        df_trigger = tf_dfs.get(timeframe, pd.DataFrame())
        if df_trigger.empty:
            update_optimization_run_status(run_id, "INSUFFICIENT_DATA", db_path=db_path)
            return run_id
            
        total_bars = len(df_trigger)
        windows = split_walk_forward_windows(
            total_bars=total_bars,
            train_window_bars=train_window_bars,
            test_window_bars=test_window_bars,
            step_bars=step_bars,
            final_holdout_bars=final_holdout_bars
        )
        
        if not windows:
            update_optimization_run_status(run_id, "INSUFFICIENT_DATA", db_path=db_path)
            return run_id
            
        completed_status = "COMPLETED"
        window_count = len(windows)
        
        all_oos_trades = []
        selected_params_per_window = []
        
        for w_idx, window in enumerate(windows):
            # Check runtime limit safety
            elapsed = time.time() - start_time
            if elapsed > max_runtime_seconds:
                completed_status = "STOPPED_BY_RUNTIME_LIMIT"
                logger.warning(f"Optimization run {run_id} hit runtime limit of {max_runtime_seconds}s. Terminating gracefully.")
                break
                
            if progress_cb:
                progress_cb(w_idx / window_count)
                
            # Slices calculation
            train_start_t = df_trigger.index[window["train_start_idx"]]
            train_end_t = df_trigger.index[window["train_end_idx"] - 1]
            test_start_t = df_trigger.index[window["test_start_idx"]]
            test_end_t = df_trigger.index[window["test_end_idx"] - 1]
            
            # Slice timeframes safely
            train_dfs = {}
            test_dfs = {}
            for tf, df_tf in tf_dfs.items():
                train_dfs[tf] = df_tf.loc[(df_tf.index >= train_start_t) & (df_tf.index <= train_end_t)]
                test_dfs[tf] = df_tf.loc[(df_tf.index >= test_start_t) & (df_tf.index <= test_end_t)]
                
            # A. Evaluate combos on Training Window
            best_params = None
            best_train_expectancy = -999.0
            best_train_metrics = {}
            
            for combo in combos:
                # Sandbox backtest run
                trades_train = run_sandbox_backtest(
                    tf_dfs=train_dfs,
                    symbol=symbol,
                    trigger_tf=timeframe,
                    params=combo,
                    start_idx_val=10, # Sliced window has shorter history
                    slippage_points=slippage_points,
                    commission_pct=commission_pct
                )
                metrics_train = calculate_metrics(trades_train)
                
                # Check for highest training expectancy
                if metrics_train["expectancy"] > best_train_expectancy:
                    best_train_expectancy = metrics_train["expectancy"]
                    best_params = combo
                    best_train_metrics = metrics_train
                    
            if not best_params:
                # If no setups triggered, fallback to first grid combo
                best_params = combos[0]
                best_train_metrics = calculate_metrics([])
                
            selected_params_per_window.append(best_params)
            
            # B. Validate out-of-sample on Testing Window
            trades_test = run_sandbox_backtest(
                tf_dfs=test_dfs,
                symbol=symbol,
                trigger_tf=timeframe,
                params=best_params,
                start_idx_val=10,
                slippage_points=slippage_points,
                commission_pct=commission_pct
            )
            metrics_test = calculate_metrics(trades_test)
            all_oos_trades.extend(trades_test)
            
            # Calculate window stability score contribution
            rob_score, rob_status = calculate_robustness_score(
                in_sample_metrics=best_train_metrics,
                out_sample_metrics=metrics_test,
                parameter_stability=100.0,
                total_oos_trades=metrics_test["total_trades"]
            )
            
            save_optimization_result(
                run_id=run_id,
                window_index=w_idx,
                train_start=str(train_start_t),
                train_end=str(train_end_t),
                test_start=str(test_start_t),
                test_end=str(test_end_t),
                params_dict=best_params,
                in_sample_metrics=best_train_metrics,
                out_sample_metrics=metrics_test,
                robustness_score=rob_score,
                warnings=oos_warnings(metrics_test),
                db_path=db_path
            )
            
        # 3. Post-run calculations
        if progress_cb:
            progress_cb(1.0)
            
        # Calculate Parameter Stability across out-of-sample windows
        # Evaluate standard deviation of thresholds, e.g. confluence_threshold
        stability = 100.0
        if len(selected_params_per_window) > 1:
            conf_vals = [p["confluence_threshold"] for p in selected_params_per_window]
            mean_conf = sum(conf_vals) / len(conf_vals)
            variance = sum((x - mean_conf) ** 2 for x in conf_vals) / len(conf_vals)
            std_dev = variance ** 0.5
            # Reduce stability by std_dev percentage
            stability = max(0.0, min(100.0, 100.0 - (std_dev * 5.0)))
            
        total_oos_trades_count = len(all_oos_trades)
        oos_summary_metrics = calculate_metrics(all_oos_trades)
        
        # Representative final parameters calculation (most selected combo)
        final_params = combos[0]
        if selected_params_per_window:
            from collections import Counter
            # Convert dict to frozen representation for counting
            frozen_params = [tuple(sorted(p.items())) for p in selected_params_per_window]
            most_common = Counter(frozen_params).most_common(1)[0][0]
            final_params = dict(most_common)
            
        # Overall robustness score
        final_robustness, final_status = calculate_robustness_score(
            in_sample_metrics=calculate_metrics([]), # Overall OOS evaluation has no single in-sample baseline
            out_sample_metrics=oos_summary_metrics,
            parameter_stability=stability,
            total_oos_trades=total_oos_trades_count
        )
        
        # 4. Save Final Recommendation
        rec_id = f"rec_{symbol}_{timeframe}_{int(time.time())}"
        valid_from_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        notes = f"Generated by walk-forward run {run_id}. Stability: {stability:.1f}%"
        if final_holdout_bars > 0:
            # Optionally validate on isolated final holdout period
            holdout_start_idx = total_bars - final_holdout_bars
            df_holdout_trigger = df_trigger.iloc[holdout_start_idx:]
            holdout_dfs = {}
            for tf, df_tf in tf_dfs.items():
                holdout_dfs[tf] = df_tf.loc[df_tf.index >= df_holdout_trigger.index[0]]
                
            holdout_trades = run_sandbox_backtest(
                tf_dfs=holdout_dfs,
                symbol=symbol,
                trigger_tf=timeframe,
                params=final_params,
                start_idx_val=10,
                slippage_points=slippage_points,
                commission_pct=commission_pct
            )
            holdout_metrics = calculate_metrics(holdout_trades)
            notes += f" | Holdout Expectancy: {holdout_metrics['expectancy']:+.2f}R ({holdout_metrics['total_trades']} trades)"
            
        save_parameter_recommendation(
            recommendation_id=rec_id,
            symbol=symbol,
            timeframe=timeframe,
            params_dict=final_params,
            robustness_score=final_robustness,
            sample_size=total_oos_trades_count,
            recommendation_status=final_status,
            valid_from=valid_from_time,
            notes=notes,
            db_path=db_path
        )
        
        update_optimization_run_status(
            run_id=run_id,
            status=completed_status,
            completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            db_path=db_path
        )
        
    except Exception as run_err:
        logger.error(f"Error executing walk-forward run {run_id}: {str(run_err)}")
        update_optimization_run_status(run_id, "FAILED", db_path=db_path)
        raise run_err
        
    return run_id

def oos_warnings(metrics: Dict[str, Any]) -> List[str]:
    warnings = []
    if metrics["total_trades"] < 5:
        warnings.append("Low trades sample size (< 5) in out-of-sample window.")
    if metrics["expectancy"] < 0:
        warnings.append("Negative net R expectancy out-of-sample.")
    return warnings
