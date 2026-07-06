import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_liquidity_zones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Liquidity Sweeps and Equal Highs/Lows based on ATR-based tolerance.
    
    Ensures 100% no-lookahead.
    """
    df = df.copy()
    df["Liquidity_Sweep"] = 0
    df["Sweep_Direction"] = "NEUTRAL"
    df["Equal_Highs"] = 0
    df["Equal_Lows"] = 0
    
    if len(df) < 3:
        return df
        
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    
    atr = df["ATR"].values if "ATR" in df.columns else (df["High"] - df["Low"]).rolling(14).mean().fillna(0.0).values
    
    # 1. Liquidity Sweep Detection
    # Bullish: Low[t] sweeps below prev Support_Level[t-1] but Close[t] closes above Support_Level[t-1]
    # Bearish: High[t] sweeps above prev Resistance_Level[t-1] but Close[t] closes below Resistance_Level[t-1]
    for t in range(1, len(df)):
        prev_support = df["Support_Level"].iloc[t-1]
        prev_resistance = df["Resistance_Level"].iloc[t-1]
        
        if pd.notna(prev_support) and prev_support > 0:
            if low[t] < prev_support and close[t] > prev_support:
                df.iloc[t, df.columns.get_loc("Liquidity_Sweep")] = 1
                df.iloc[t, df.columns.get_loc("Sweep_Direction")] = "BULLISH"
                
        if pd.notna(prev_resistance) and prev_resistance > 0:
            if high[t] > prev_resistance and close[t] < prev_resistance:
                df.iloc[t, df.columns.get_loc("Liquidity_Sweep")] = 1
                df.iloc[t, df.columns.get_loc("Sweep_Direction")] = "BEARISH"
                
    # 2. Equal Highs / Equal Lows (EQH / EQL)
    # Detects if the current confirmed swing level is close to the previous swing level
    # within 0.15 * ATR tolerance.
    swing_highs = []
    swing_lows = []
    
    for t in range(len(df)):
        sh = df["Swing_High"].iloc[t]
        sl = df["Swing_Low"].iloc[t]
        curr_atr = atr[t] if atr[t] > 0 else df["Close"].iloc[t] * 0.01
        tol = 0.15 * curr_atr
        
        if pd.notna(sh) and sh > 0:
            if swing_highs:
                prev_sh = swing_highs[-1]
                if abs(sh - prev_sh) <= tol:
                    df.iloc[t, df.columns.get_loc("Equal_Highs")] = 1
            swing_highs.append(sh)
            
        if pd.notna(sl) and sl > 0:
            if swing_lows:
                prev_sl = swing_lows[-1]
                if abs(sl - prev_sl) <= tol:
                    df.iloc[t, df.columns.get_loc("Equal_Lows")] = 1
            swing_lows.append(sl)
            
    return df
