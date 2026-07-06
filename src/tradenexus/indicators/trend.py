import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import logging

logger = logging.getLogger(__name__)

def calculate_cdc_actionzone(df: pd.DataFrame, fast_len: int = 12, slow_len: int = 26) -> pd.DataFrame:
    """
    Calculates the CDC ActionZone (Simplified).
    - Bullish Trend (Green): EMA(fast) > EMA(slow)
    - Bearish Trend (Red): EMA(fast) < EMA(slow)
    
    Adds columns:
    - 'EMA_Fast': Fast EMA
    - 'EMA_Slow': Slow EMA
    - 'CDC_Trend': 'Bullish' or 'Bearish'
    - 'CDC_Signal': 'Buy', 'Sell', or 'Hold'
    """
    if len(df) < max(fast_len, slow_len):
        logger.warning("Dataframe length too short for CDC calculation.")
        df["EMA_Fast"] = np.nan
        df["EMA_Slow"] = np.nan
        df["CDC_Trend"] = "Neutral"
        df["CDC_Signal"] = "Hold"
        return df

    df = df.copy()
    
    # Calculate EMAs using pandas ewm for numerical stability
    df["EMA_Fast"] = df["Close"].ewm(span=fast_len, adjust=False).mean()
    df["EMA_Slow"] = df["Close"].ewm(span=slow_len, adjust=False).mean()
    
    # Determine Trend
    df["CDC_Trend"] = np.where(df["EMA_Fast"] > df["EMA_Slow"], "Bullish", "Bearish")
    
    # Signal Crossovers
    prev_trend = df["CDC_Trend"].shift(1)
    
    df["CDC_Signal"] = "Hold"
    df.loc[(df["CDC_Trend"] == "Bullish") & (prev_trend == "Bearish"), "CDC_Signal"] = "Buy"
    df.loc[(df["CDC_Trend"] == "Bearish") & (prev_trend == "Bullish"), "CDC_Signal"] = "Sell"
    
    return df

def calculate_adaptive_trend(df: pd.DataFrame, period: int = 10, fast: int = 2, slow: int = 30) -> pd.DataFrame:
    """
    Adaptive Trend Finder using Kaufman's Adaptive Moving Average (KAMA)
    and ATR-based SuperTrend.
    """
    df = df.copy()
    if len(df) < period + 2:
        df["KAMA"] = df["Close"]
        df["Adaptive_Trend"] = "Neutral"
        df["SuperTrend"] = df["Close"]
        df["SuperTrend_Direction"] = "Neutral"
        return df
        
    close = df["Close"].values
    kama = np.zeros(len(df))
    kama[period - 1] = close[period - 1]
    
    direction = np.abs(df["Close"] - df["Close"].shift(period))
    volatility = np.abs(df["Close"] - df["Close"].shift(1)).rolling(window=period).sum()
    
    er = np.zeros(len(df))
    with np.errstate(divide='ignore', invalid='ignore'):
        er = np.where(volatility > 0, direction / volatility, 0)
    
    fast_sc = 2.0 / (fast + 1)
    slow_sc = 2.0 / (slow + 1)
    
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    
    for i in range(period, len(df)):
        kama[i] = kama[i-1] + sc[i] * (close[i] - kama[i-1])
        
    df["KAMA"] = kama
    df.loc[df["KAMA"] == 0, "KAMA"] = df["Close"]
    
    df["Adaptive_Trend"] = np.where(df["Close"] > df["KAMA"], "Bullish", "Bearish")
    
    try:
        st_df = ta.supertrend(df["High"], df["Low"], df["Close"], length=10, multiplier=3.0)
        if st_df is not None and not st_df.empty:
            df["SuperTrend"] = st_df.iloc[:, 0]
            df["SuperTrend_Direction"] = np.where(st_df.iloc[:, 1] > 0, "Bullish", "Bearish")
        else:
            df["SuperTrend"] = df["KAMA"]
            df["SuperTrend_Direction"] = df["Adaptive_Trend"]
    except Exception as e:
        logger.warning(f"SuperTrend failed: {str(e)}")
        df["SuperTrend"] = df["KAMA"]
        df["SuperTrend_Direction"] = df["Adaptive_Trend"]
        
    return df
