import logging

logger = logging.getLogger(__name__)

def calculate_confluence_score(latest_data: dict) -> dict:
    """
    Confluence Score 2.0.
    
    Computes directional alignment and setup quality based on indicators,
    market regime, volume flows, and risk parameters.
    
    Weights (Quality Score 0-100):
    - Trend agreement: 25 points
    - Momentum strength: 15 points
    - SMC structure: 20 points
    - Market regime: 15 points
    - Volume / VWAP confirmation: 10 points
    - Risk/Reward quality: 15 points
    """
    reasons = []
    warnings = []
    
    # 1. Directional Score Calculation (-100 to +100)
    dir_score = 0.0
    
    cdc_trend = latest_data.get("CDC_Trend", "Neutral")
    supertrend_dir = latest_data.get("SuperTrend_Direction", "Neutral")
    macd_trend = latest_data.get("MACD_Trend", "Neutral")
    kama_trend = latest_data.get("Adaptive_Trend", "Neutral")
    
    if cdc_trend == "Bullish":
        dir_score += 40.0
        reasons.append("CDC ActionZone Bullish (+40)")
    elif cdc_trend == "Bearish":
        dir_score -= 40.0
        reasons.append("CDC ActionZone Bearish (-40)")
        
    if supertrend_dir == "Bullish":
        dir_score += 40.0
        reasons.append("SuperTrend Bullish (+40)")
    elif supertrend_dir == "Bearish":
        dir_score -= 40.0
        reasons.append("SuperTrend Bearish (-40)")
        
    if macd_trend == "Bullish":
        dir_score += 10.0
        reasons.append("MACD Bullish (+10)")
    elif macd_trend == "Bearish":
        dir_score -= 10.0
        reasons.append("MACD Bearish (-10)")
        
    if kama_trend == "Bullish":
        dir_score += 10.0
        reasons.append("KAMA Bullish (+10)")
    elif kama_trend == "Bearish":
        dir_score -= 10.0
        reasons.append("KAMA Bearish (-10)")
        
    is_bullish = dir_score > 0
    
    # 2. Quality Score 2.0 (0 to 100)
    q_score = 0.0
    
    # A. Trend agreement (max 25 points)
    if cdc_trend == supertrend_dir and cdc_trend != "Neutral":
        q_score += 25.0
        reasons.append("Daily and intermediate trends fully aligned (+25)")
    elif cdc_trend != "Neutral" or supertrend_dir != "Neutral":
        q_score += 12.5
        reasons.append("Partial trend alignment (+12.5)")
        
    # B. Momentum strength (max 15 points)
    adx = latest_data.get("ADX", 20.0)
    if adx >= 25:
        q_score += 15.0
        reasons.append(f"Strong ADX trend strength ({adx:.1f} >= 25) (+15)")
    elif adx < 20:
        q_score += 5.0
        warnings.append(f"Weak ADX trend strength ({adx:.1f} < 20) (-10)")
    else:
        q_score += 10.0
        
    # C. SMC structure (max 20 points)
    support_src = latest_data.get("Support_Source", "FALLBACK")
    resistance_src = latest_data.get("Resistance_Source", "FALLBACK")
    relevant_src = support_src if is_bullish else resistance_src
    
    if relevant_src == "CONFIRMED_SWING":
        q_score += 15.0
        reasons.append("Using confirmed swing S/R levels (+15)")
    else:
        q_score += 5.0
        warnings.append("Using fallback S/R levels (-10)")
        
    # Check for active structures (BOS, CHOCH, FVG)
    bos = latest_data.get("BOS_Present", 0)
    choch = latest_data.get("CHOCH_Present", 0)
    fvg = latest_data.get("FVG_Present", 0)
    
    if bos or choch or fvg:
        q_score += 5.0
        reasons.append("Supporting structural break / gap active (+5)")
        
    # D. Market Regime (max 15 points)
    regime = latest_data.get("primary_regime", "UNKNOWN")
    regime_score = latest_data.get("regime_score", 50.0)
    regime_flags = latest_data.get("regime_flags", "")
    
    if regime in ["TRENDING_UP", "TRENDING_DOWN", "EXPANSION"]:
        q_score += 15.0
        reasons.append(f"Market regime supports active strategy ({regime}) (+15)")
    elif regime in ["SIDEWAYS", "SQUEEZE"]:
        q_score += 5.0
        warnings.append(f"Market is sideways/squeezed ({regime}) - entry quality reduced (-10)")
    else:
        q_score += 10.0
        
    if "HIGH_VOLATILITY" in regime_flags:
        q_score -= 5.0
        warnings.append("High volatility flag active - increased stop risk (-5)")
    if "LOW_LIQUIDITY" in regime_flags:
        q_score -= 10.0
        warnings.append("Low liquidity flag active - increased slippage risk (-10)")
        
    # E. Volume / VWAP Confirmation (max 10 points)
    has_vol_warning = (latest_data.get("Volume_Warning", "") != "")
    vol_conf = latest_data.get("Volume_Confirmation", "NEUTRAL")
    
    vwap = latest_data.get("VWAP", latest_data.get("Close"))
    price = latest_data.get("Close")
    
    vwap_bull = price > vwap
    vwap_bear = price < vwap
    
    if has_vol_warning:
        q_score += 5.0  # Neutral contribution
        warnings.append("Volume indicators neutral (data unavailable/unreliable)")
    else:
        # VWAP alignment (5 points)
        if (is_bullish and vwap_bull) or (not is_bullish and vwap_bear):
            q_score += 5.0
            reasons.append("Price aligned with VWAP trend (+5)")
            
        # Volume Flow Confirmation (5 points)
        if (is_bullish and vol_conf == "BULLISH") or (not is_bullish and vol_conf == "BEARISH"):
            q_score += 5.0
            reasons.append("Volume flow confirms breakout direction (+5)")
        else:
            q_score += 2.0
            
    # F. Risk/Reward quality (max 15 points)
    rr_tp1 = latest_data.get("RR_TP1", 0.0)
    if rr_tp1 >= 1.5:
        q_score += 15.0
        reasons.append(f"High risk-to-reward ratio ({rr_tp1:.2f} >= 1.5) (+15)")
    else:
        q_score += 0.0
        warnings.append(f"Suboptimal risk-to-reward ratio ({rr_tp1:.2f} < 1.5)")
        
    # 3. Combine into Confluence Score (0 to 100)
    # We define confluence score as 50% directional strength + 50% setup quality
    conf_score = (abs(dir_score) * 0.5) + (q_score * 0.5)
    
    # Safe bounds
    dir_score = max(min(dir_score, 100.0), -100.0)
    q_score = max(min(q_score, 100.0), 0.0)
    conf_score = max(min(conf_score, 100.0), 0.0)
    
    return {
        "directional_score": dir_score,
        "quality_score": q_score,
        "confluence_score": conf_score,
        "reasons": reasons,
        "warnings": warnings
    }
