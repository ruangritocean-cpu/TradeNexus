import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def build_reasons(data: Dict[str, Any]) -> List[str]:
    """
    Generates human-readable, deterministic explanations based ONLY on existing computed fields.
    """
    reasons = []
    
    # 1. MTF Hierarchy Trend explanation
    bias_1d = data.get("market_bias", data.get("bias_1d", "Neutral"))
    setup_4h = data.get("setup_direction", data.get("setup_4h", "Neutral"))
    trigger_1h = data.get("trigger_direction", data.get("trigger_1h", "Neutral"))
    alignment = data.get("alignment_type", "CONFLICTED")
    
    if alignment == "TREND_FOLLOWING":
        reasons.append(f"Trend hierarchy is aligned (1D Bias: {bias_1d}, 4H Setup: {setup_4h}).")
    elif alignment == "COUNTER_TREND_SCALP":
        reasons.append(f"Counter-trend scalp setup detected (1D Bias: {bias_1d}, 1H Trigger: {trigger_1h}).")
    else:
        reasons.append(f"Conflicted trend alignment across timeframes (1D: {bias_1d}, 4H: {setup_4h}).")
        
    # 2. Confluence Score & Key Indicators
    conf_score = data.get("confluence_score", 0.0)
    reasons.append(f"Confluence score of {conf_score:.0f}/100 indicates moderate-to-high signal strength.")
    
    # 3. Market Regime & Flags
    regime = data.get("primary_regime", "UNKNOWN")
    flags_raw = data.get("regime_flags", [])
    if isinstance(flags_raw, str):
        flags = flags_raw.split(",") if flags_raw else []
    else:
        flags = flags_raw
        
    reasons.append(f"Market regime classified as {regime} with flags: {', '.join(flags) if flags else 'None'}.")
    
    # 4. VWAP / Volume confirmations
    vwap_align = data.get("vwap_alignment", "NEUTRAL")
    vol_conf = data.get("volume_confirmation", "NEUTRAL")
    if vwap_align != "NEUTRAL":
        reasons.append(f"VWAP position is {vwap_align}, confirming direction.")
    if vol_conf == "BULLISH_VOLUME":
        reasons.append("Volume confirmation is Bullish, showing high buyer participation.")
    elif vol_conf == "BEARISH_VOLUME":
        reasons.append("Volume confirmation is Bearish, showing high seller participation.")
        
    # 5. SMC Structures
    bos = data.get("bos_present", 0)
    choch = data.get("choch_present", 0)
    fvg = data.get("fvg_present", 0)
    
    if bos:
        reasons.append("Break of Structure (BOS) confirms continuation.")
    if choch:
        reasons.append("Change of Character (CHOCH) indicates early trend reversal.")
    if fvg:
        reasons.append("Fair Value Gap (FVG) represents liquidity imbalance target.")
        
    # 6. Risk / Reward validation
    rr_tp1 = data.get("rr_tp1", 0.0)
    if rr_tp1 > 0:
        reasons.append(f"Risk/Reward ratio of {rr_tp1:.2f}R to TP1 satisfies the minimum veto threshold.")
        
    return reasons
