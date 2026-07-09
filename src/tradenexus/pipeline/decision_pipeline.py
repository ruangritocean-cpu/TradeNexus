import logging
from typing import Dict, Any, Tuple
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk
from tradenexus.signals.state import is_trade_active

logger = logging.getLogger(__name__)

def evaluate_decision_and_scoring(
    latest_15m: Dict[str, Any],
    latest_1h: Dict[str, Any],
    latest_4h: Dict[str, Any],
    latest_1d: Dict[str, Any],
    timeframe: str,
    min_confluence_score: float = 70.0,
    min_rr: float = 1.5
) -> Dict[str, Any]:
    """
    Unified decision making and scoring pipeline.
    Combines MTF hierarchy check, regime filters, R/R check, and computes confluence.
    """
    # 1. Select the target timeframe row to base our signals and scoring on
    target_row = latest_1h
    if timeframe == "15m":
        target_row = latest_15m
    elif timeframe == "4h":
        target_row = latest_4h
    elif timeframe == "1d":
        target_row = latest_1d
        
    score_res = calculate_confluence_score(target_row)
    dir_score = score_res["directional_score"]
    
    # Map raw trade direction based on directional score
    direction = "NEUTRAL"
    if dir_score >= 60:
        direction = "BUY"
    elif dir_score <= -60:
        direction = "SELL"
        
    # 2. Evaluate MTF Hierarchy alignment
    bias_1d = latest_1d.get("CDC_Trend", "Neutral")
    setup_4h = latest_4h.get("CDC_Trend", "Neutral")
    trigger_1h = latest_1h.get("CDC_Trend", "Neutral")
    exec_15m = latest_15m.get("CDC_Trend", "Neutral")
    
    mtf_res = evaluate_mtf_hierarchy(
        bias_1d=bias_1d,
        setup_4h=setup_4h,
        trigger_1h=trigger_1h,
        exec_15m=exec_15m
    )
    alignment_type = mtf_res["alignment_type"]
    
    # 3. Check Risk/Reward Veto
    support_val = target_row.get("Support_Level", 0.0)
    resistance_val = target_row.get("Resistance_Level", 0.0)
    atr_val = target_row.get("ATR", 0.0)
    close_price = target_row.get("Close", 0.0)
    
    risk_res = validate_trade_risk(
        price=close_price,
        decision=direction,
        support=support_val,
        resistance=resistance_val,
        atr=atr_val,
        rr_min=min_rr
    )
    
    # Inject calculated RR back into scoring to update quality score
    target_row_updated = dict(target_row)
    target_row_updated["RR_TP1"] = risk_res["RR_TP1"]
    score_res = calculate_confluence_score(target_row_updated)
    
    # 4. Determine initial decision state
    decision_state = "NO TRADE"
    if is_trade_active():
        decision_state = "MANAGE TRADE"
    elif risk_res["Vetoed"]:
        decision_state = "NO TRADE"
    elif direction == "NEUTRAL":
        decision_state = "WATCH"
    else: # BUY/SELL
        if alignment_type in ["TREND_FOLLOWING", "COUNTER_TREND_SCALP"]:
            if score_res["confluence_score"] >= min_confluence_score:
                decision_state = "ENTRY TRIGGERED"
            else:
                decision_state = "READY"
        else:
            decision_state = "WATCH"
            
    # 5. Apply Regime-Aware overrides
    primary_regime = target_row.get("primary_regime", "UNKNOWN")
    regime_flags_str = target_row.get("regime_flags", "")
    regime_flags = regime_flags_str.split(",") if regime_flags_str else []
    
    final_state, regime_reasons, regime_warnings = apply_regime_decision_rules(
        decision_state=decision_state,
        primary_regime=primary_regime,
        flags=regime_flags,
        direction=direction
    )
    
    all_reasons = score_res["reasons"] + mtf_res["reasons"] + regime_reasons
    all_warnings = score_res["warnings"] + mtf_res["warnings"] + regime_warnings
    
    return {
        "decision_state": final_state,
        "direction": direction,
        "alignment_type": alignment_type,
        "confluence_score": score_res["confluence_score"],
        "directional_score": dir_score,
        "quality_score": score_res["quality_score"],
        "reasons": all_reasons,
        "warnings": all_warnings,
        "rr_tp1": risk_res["RR_TP1"],
        "primary_regime": primary_regime,
        "regime_flags": regime_flags
    }
