import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_smc_lite(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    SMC Confirmed Swing Engine (No-Repaint / No Look-Ahead).
    
    A Swing High/Low at index 't' is only confirmed after 'k' candles of 
    lookforward have closed (where k = window // 2). 
    
    Variables:
    - swing_time = The actual time of the swing candle (index t).
    - confirmed_at = The time the swing was confirmed (index t + k).
    - level_active_from = confirmed_at (the level is only active/available to the system
      from this timestamp onwards).
      
    This logic prevents look-ahead bias in backtests and live trading signals.
    """
    df = df.copy()
    df["Swing_High"] = np.nan
    df["Swing_Low"] = np.nan
    df["Support_Level"] = np.nan
    df["Resistance_Level"] = np.nan
    df["Support_Source"] = "FALLBACK"
    df["Resistance_Source"] = "FALLBACK"
    
    k = window // 2  # default 10 for window = 20
    
    if len(df) < window:
        df["Support_Level"] = df["Low"].cummin()
        df["Resistance_Level"] = df["High"].cummax()
        return df

    high_vals = df["High"].values
    low_vals = df["Low"].values
    
    confirmed_lows = []
    confirmed_highs = []
    
    for i in range(k, len(df) - k):
        # 1. Swing High Detection (peak at index i)
        center_high = high_vals[i]
        is_high = True
        for j in range(i - k, i + k + 1):
            if high_vals[j] > center_high:
                is_high = False
                break
        if is_high:
            df.iloc[i, df.columns.get_loc("Swing_High")] = center_high
            confirmed_highs.append((i + k, center_high))
            
        # 2. Swing Low Detection (trough at index i)
        center_low = low_vals[i]
        is_low = True
        for j in range(i - k, i + k + 1):
            if low_vals[j] < center_low:
                is_low = False
                break
        if is_low:
            df.iloc[i, df.columns.get_loc("Swing_Low")] = center_low
            confirmed_lows.append((i + k, center_low))
            
    # Calculate S/R levels active ONLY from the confirmation point onward
    curr_support = np.nan
    for idx in range(len(df)):
        active_lows = [val for conf_idx, val in confirmed_lows if conf_idx <= idx]
        if active_lows:
            curr_support = active_lows[-1]
            df.iloc[idx, df.columns.get_loc("Support_Level")] = curr_support
            df.iloc[idx, df.columns.get_loc("Support_Source")] = "CONFIRMED_SWING"
        else:
            # Fallback
            df.iloc[idx, df.columns.get_loc("Support_Level")] = df["Low"].iloc[:idx+1].min()
            df.iloc[idx, df.columns.get_loc("Support_Source")] = "FALLBACK"
            
    curr_resistance = np.nan
    for idx in range(len(df)):
        active_highs = [val for conf_idx, val in confirmed_highs if conf_idx <= idx]
        if active_highs:
            curr_resistance = active_highs[-1]
            df.iloc[idx, df.columns.get_loc("Resistance_Level")] = curr_resistance
            df.iloc[idx, df.columns.get_loc("Resistance_Source")] = "CONFIRMED_SWING"
        else:
            # Fallback
            df.iloc[idx, df.columns.get_loc("Resistance_Level")] = df["High"].iloc[:idx+1].max()
            df.iloc[idx, df.columns.get_loc("Resistance_Source")] = "FALLBACK"
            
    return df
