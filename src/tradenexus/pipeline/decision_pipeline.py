import logging
from typing import Dict, Any, Tuple
from tradenexus.signals.scoring import calculate_confluence_score
from tradenexus.signals.rules import evaluate_mtf_hierarchy, apply_regime_decision_rules
from tradenexus.signals.risk import validate_trade_risk

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
    # 1. Calculate Confluence Score
    # We use the selected timeframe's latest data row to calculate confluence score
    target_row = latest_1h
    if timeframe == "15m":
        target_row = latest_15m
    elif timeframe == "4h":
        target_row = latest_4h
    elif timeframe == "1d":
        target_row = latest_1d
        
    score_res = calculate_confluence_score(target_row)
    
    # 2. Evaluate MTF Hierarchy Decision State
    mtf_state, alignment_type, mtf_dir, base_dec = evaluate_mtf_hierarchy(
        bias_1d=latest_1d.get("market_bias", "Neutral"),
        setup_4h=latest_4h.get("setup_direction", "Neutral"),
        trigger_1h=latest_1h.get("trigger_direction", "Neutral"),
        trigger_15m=latest_15m.get("trigger_direction", "Neutral"),
        timeframe=timeframe
    )
    
    # Extract regime settings from target row
    primary_regime = target_row.get("primary_regime", "UNKNOWN")
    regime_flags_str = target_row.get("regime_flags", "")
    regime_flags = regime_flags_str.split(",") if regime_flags_str else []
    
    # 3. Apply Regime override rules
    final_state, regime_reasons, regime_warnings = apply_regime_decision_rules(
        decision_state=mtf_state,
        primary_regime=primary_regime,
        flags=regime_flags,
        direction=base_dec
    )
    
    # 4. Check Risk/Reward Veto
    rr_tp1 = target_row.get("RR_TP1", 0.0)
    risk_valid, risk_reasons, risk_warnings = validate_trade_risk(
        decision_state=final_state,
        rr_tp1=rr_tp1,
        min_rr_threshold=min_rr
    )
    
    if final_state == "ENTRY TRIGGERED" and not risk_valid:
        final_state = "WATCH"
        
    all_reasons = score_res["reasons"] + regime_reasons + risk_reasons
    all_warnings = score_res["warnings"] + regime_warnings + risk_warnings
    
    return {
        "decision_state": final_state,
        "direction": base_dec,
        "alignment_type": alignment_type,
        "confluence_score": score_res["confluence_score"],
        "directional_score": score_res["directional_score"],
        "quality_score": score_res["quality_score"],
        "reasons": all_reasons,
        "warnings": all_warnings,
        "rr_tp1": rr_tp1,
        "primary_regime": primary_regime,
        "regime_flags": regime_flags
    }
