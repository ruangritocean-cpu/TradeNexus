import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def classify_market_regime(df: pd.DataFrame) -> dict:
    """
    Market Regime Classifier.
    
    Classifies current market condition into a primary regime and adds warning/regime flags.
    
    Primary Regimes:
    - TRENDING_UP
    - TRENDING_DOWN
    - SIDEWAYS
    - SQUEEZE
    - EXPANSION
    - UNKNOWN
    
    Flags:
    - HIGH_VOLATILITY
    - LOW_LIQUIDITY
    - VOLUME_UNRELIABLE
    - INSUFFICIENT_DATA
    """
    if df.empty or len(df) < 30:
        return {
            "primary_regime": "UNKNOWN",
            "flags": ["INSUFFICIENT_DATA"],
            "regime_score": 0.0,
            "reasons": ["Dataset too short for reliable classification (minimum 30 rows)."],
            "warnings": ["Insufficient historical data."]
        }
        
    reasons = []
    warnings = []
    flags = []
    
    latest = df.iloc[-1]
    
    # 1. Retrieve or calculate needed parameters
    adx = latest.get("ADX", 20.0)
    atr = latest.get("ATR", 0.0)
    
    # Compute ATR percentile relative to history
    atr_series = df["ATR"].dropna() if "ATR" in df.columns else pd.Series(dtype=float)
    if not atr_series.empty:
        atr_pct = (atr_series < atr).mean() * 100.0
    else:
        atr_pct = 50.0
        
    # Bollinger Bandwidth
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns and "BB_Middle" in df.columns:
        bb_upper = df["BB_Upper"]
        bb_lower = df["BB_Lower"]
        bb_middle = df["BB_Middle"]
        bandwidth = (bb_upper - bb_lower) / bb_middle
        latest_bw = bandwidth.iloc[-1]
        bw_pct = (bandwidth < latest_bw).mean() * 100.0
    else:
        latest_bw = 0.0
        bw_pct = 50.0
        
    # Check volume quality
    has_valid_vol = True
    if "Volume" not in df.columns or df["Volume"].isna().all() or df["Volume"].sum() == 0:
        has_valid_vol = False
        flags.append("VOLUME_UNRELIABLE")
        warnings.append("Volume data is unavailable or unreliable.")
        
    # 2. Flag checks
    if atr_pct >= 85.0:
        flags.append("HIGH_VOLATILITY")
        warnings.append("High volatility expansion active (ATR in top 15%).")
        
    # Simple low liquidity check (extremely narrow ATR/spread)
    if atr_pct <= 15.0:
        flags.append("LOW_LIQUIDITY")
        warnings.append("Low liquidity warning (ATR in bottom 15%).")
        
    # 3. Classify Primary Regime
    # Check EMA alignment or KAMA trend for direction
    fast_ema = latest.get("EMA_Fast", latest.get("Close"))
    slow_ema = latest.get("EMA_Slow", latest.get("Close"))
    
    is_bullish = fast_ema > slow_ema
    is_bearish = fast_ema < slow_ema
    
    # We also check if price is relative to VWAP if available
    vwap = latest.get("VWAP", latest.get("Close"))
    price = latest["Close"]
    
    if price > vwap:
        is_bullish = is_bullish or True
    elif price < vwap:
        is_bearish = is_bearish or True
        
    # Classification Logic
    primary_regime = "SIDEWAYS"
    regime_score = 50.0
    
    if adx >= 25:
        if is_bullish:
            primary_regime = "TRENDING_UP"
            regime_score = min(50.0 + (adx - 25.0) * 2.0, 100.0)
            reasons.append(f"Strong upward trend confirmed by ADX ({adx:.1f} >= 25)")
        elif is_bearish:
            primary_regime = "TRENDING_DOWN"
            regime_score = min(50.0 + (adx - 25.0) * 2.0, 100.0)
            reasons.append(f"Strong downward trend confirmed by ADX ({adx:.1f} >= 25)")
    else: # ADX < 25
        # Check for squeeze (bandwidth percentile <= 20)
        if bw_pct <= 20.0:
            primary_regime = "SQUEEZE"
            regime_score = 100.0 - bw_pct
            reasons.append(f"Bollinger Bands compressed in squeeze state (bandwidth percentile: {bw_pct:.1f}%)")
        else:
            # Check for expansion: if bandwidth was squeezed recently (last 5 bars) and bandwidth is expanding
            was_squeezed = False
            if "BB_Upper" in df.columns:
                recent_bw_pcts = [((bandwidth < b).mean() * 100.0) for b in bandwidth.tail(6)]
                if any(p <= 20.0 for p in recent_bw_pcts[:-1]) and bw_pct > 25.0:
                    was_squeezed = True
                    
            if was_squeezed and atr_pct > 50.0:
                primary_regime = "EXPANSION"
                regime_score = min(50.0 + (atr_pct - 50.0) * 2.0, 100.0)
                reasons.append("Volatility expanding out of a recent squeeze.")
            else:
                primary_regime = "SIDEWAYS"
                regime_score = 50.0 - adx
                reasons.append(f"Low trend strength sideways market (ADX: {adx:.1f} < 25)")
                
    return {
        "primary_regime": primary_regime,
        "flags": flags,
        "regime_score": regime_score,
        "reasons": reasons,
        "warnings": warnings
    }
