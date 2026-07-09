import logging

logger = logging.getLogger(__name__)

def evaluate_mtf_hierarchy(
    bias_1d: str, 
    setup_4h: str, 
    trigger_1h: str, 
    exec_15m: str
) -> dict:
    """
    Evaluates the Multi-Timeframe (MTF) Hierarchy:
    - 1D = Market Bias
    - 4H = Setup Direction
    - 1H = Trigger Direction
    - 15m = Execution Direction
    
    Returns:
        dict: {
            "market_bias": str,
            "setup_direction": str,
            "trigger_direction": str,
            "execution_direction": str,
            "alignment_type": str ('TREND_FOLLOWING', 'COUNTER_TREND_SCALP', 'CONFLICTED'),
            "reasons": list[str],
            "warnings": list[str]
        }
    """
    reasons = []
    warnings = []
    
    # 1. Classify Alignment Type
    alignment_type = "CONFLICTED"
    
    # Check Trend Following Buy: 1D, 4H, and 1H are Bullish
    if bias_1d == "Bullish" and setup_4h == "Bullish" and trigger_1h == "Bullish":
        alignment_type = "TREND_FOLLOWING"
        reasons.append("Bullish Trend Following Setup aligned across 1D, 4H, and 1H.")
        
    # Check Trend Following Sell: 1D, 4H, and 1H are Bearish
    elif bias_1d == "Bearish" and setup_4h == "Bearish" and trigger_1h == "Bearish":
        alignment_type = "TREND_FOLLOWING"
        reasons.append("Bearish Trend Following Setup aligned across 1D, 4H, and 1H.")
        
    # Check Counter-Trend Scalp Buy: Higher timeframes (1D/4H) are Bearish, but lower (1H/15m) are Bullish
    elif (bias_1d == "Bearish" or setup_4h == "Bearish") and trigger_1h == "Bullish" and exec_15m == "Bullish":
        alignment_type = "COUNTER_TREND_SCALP"
        reasons.append("Counter-Trend Scalp Buy: Lower timeframes (1H, 15m) are turning bullish against daily bearish trend.")
        warnings.append("⚠️ Counter-Trend trade: High risk. Maintain tight risk controls.")
        
    # Check Counter-Trend Scalp Sell: Higher timeframes (1D/4H) are Bullish, but lower (1H/15m) are Bearish
    elif (bias_1d == "Bullish" or setup_4h == "Bullish") and trigger_1h == "Bearish" and exec_15m == "Bearish":
        alignment_type = "COUNTER_TREND_SCALP"
        reasons.append("Counter-Trend Scalp Sell: Lower timeframes (1H, 15m) are turning bearish against daily bullish trend.")
        warnings.append("⚠️ Counter-Trend trade: High risk. Maintain tight risk controls.")
        
    else:
        alignment_type = "CONFLICTED"
        warnings.append("Timeframes are conflicted. Sideways or rotational market environment.")
        
    return {
        "market_bias": bias_1d,
        "setup_direction": setup_4h,
        "trigger_direction": trigger_1h,
        "execution_direction": exec_15m,
        "alignment_type": alignment_type,
        "reasons": reasons,
        "warnings": warnings
    }

def apply_regime_decision_rules(
    decision_state: str,
    primary_regime: str = "UNKNOWN",
    flags: list[str] | None = None,
    confluence_score: float = 0.0,
) -> tuple[str, list[str], list[str]]:
    """
    Regime-Aware Decision Engine.
    
    Applies conditional overrides to decision state based on the current market regime.
    
    Returns:
        tuple[str, list[str], list[str]]: (final_decision_state, new_reasons, new_warnings)
    """
    new_reasons = []
    new_warnings = []
    
    final_state = decision_state
    
    # Normalize flags safely
    if flags is None:
        flags = []
    elif isinstance(flags, str):
        flags = [x.strip() for x in flags.split(",") if x.strip()]
    else:
        flags = list(flags)
        
    # Ensure primary_regime is normalized
    if not primary_regime:
        primary_regime = "UNKNOWN"
        
    # 1. Sideways Filter: block weak trend entries
    if primary_regime == "SIDEWAYS" and decision_state == "ENTRY TRIGGERED":
        if confluence_score < 80.0:
            final_state = "WATCH"
            new_warnings.append("Sideways regime blocks weak trend entries (requires confluence >= 80%).")
            
    # 2. Squeeze Filter: block entries until breakout closes
    elif primary_regime == "SQUEEZE" and decision_state == "ENTRY TRIGGERED":
        final_state = "WATCH"
        new_warnings.append("Squeeze compression blocks entry trigger before breakout candle closes.")
        
    # 3. Low Liquidity Filter: locks all entry setups to avoid slippage
    if "LOW_LIQUIDITY" in flags:
        if final_state in ["ENTRY TRIGGERED", "READY"]:
            final_state = "WATCH"
            new_warnings.append("Low liquidity environment blocks entry triggers to prevent execution slippage.")
            
    # 4. High Volatility warning
    if "HIGH_VOLATILITY" in flags:
        if final_state == "ENTRY TRIGGERED":
            new_reasons.append("Entry trigger allowed in high volatility (widen stops if necessary).")
            new_warnings.append("High volatility active. Widen SL ATR buffer to prevent noise hits.")
            
    return final_state, new_reasons, new_warnings
