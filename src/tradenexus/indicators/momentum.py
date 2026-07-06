import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import logging

logger = logging.getLogger(__name__)

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates MACD (12, 26, 9) and trends.
    """
    if len(df) < max(fast, slow) + signal:
        df["MACD"] = np.nan
        df["MACD_Signal"] = np.nan
        df["MACD_Hist"] = np.nan
        df["MACD_Trend"] = "Neutral"
        df["MACD_Crossover"] = "None"
        return df
        
    df = df.copy()
    
    macd_df = ta.macd(df["Close"], fast=fast, slow=slow, signal=signal)
    if macd_df is not None and not macd_df.empty:
        df["MACD"] = macd_df.iloc[:, 0]
        df["MACD_Hist"] = macd_df.iloc[:, 1]
        df["MACD_Signal"] = macd_df.iloc[:, 2]
    else:
        fast_ema = df["Close"].ewm(span=fast, adjust=False).mean()
        slow_ema = df["Close"].ewm(span=slow, adjust=False).mean()
        df["MACD"] = fast_ema - slow_ema
        df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
        
    df["MACD_Trend"] = np.where(df["MACD"] > df["MACD_Signal"], "Bullish", "Bearish")
    
    prev_macd_trend = df["MACD_Trend"].shift(1)
    df["MACD_Crossover"] = "None"
    df.loc[(df["MACD_Trend"] == "Bullish") & (prev_macd_trend == "Bearish"), "MACD_Crossover"] = "Bullish Crossover"
    df.loc[(df["MACD_Trend"] == "Bearish") & (prev_macd_trend == "Bullish"), "MACD_Crossover"] = "Bearish Crossover"
    
    return df

def calculate_adx(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """
    Calculates Average Directional Index (ADX) and strength categories.
    """
    df = df.copy()
    if len(df) < 2 * length:
        df["ADX"] = np.nan
        df["ADX_Strength"] = "Sideways"
        return df

    adx_df = ta.adx(df["High"], df["Low"], df["Close"], length=length)
    if adx_df is not None and not adx_df.empty:
        df["ADX"] = adx_df.iloc[:, 0]
    else:
        df["ADX"] = np.nan
        
    df["ADX"] = df["ADX"].bfill().fillna(20.0)
    df["ADX_Strength"] = np.where(df["ADX"] >= 25, "Strong Trend", 
                                  np.where(df["ADX"] < 20, "Sideways", "Weak Trend"))
    return df
