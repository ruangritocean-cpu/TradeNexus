import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import logging

logger = logging.getLogger(__name__)

def calculate_mcdx_proxy(df: pd.DataFrame, rsi_len: int = 14, atr_len: int = 14) -> pd.DataFrame:
    """
    MCDX (Proxy): Calculate RSI (14) and multiply by volatility factor (ATR 14)
    to create a custom momentum strength oscillator.
    
    Also provides a classic MCDX "Smart Money Flow" calculation:
    - Retailer (Green): Base RSI levels representing low volume/retail
    - Hot Money (Yellow): Mid RSI levels representing hot money
    - Smart Money (Red): Banker/Smart money based on high RSI levels smoothed
    """
    if len(df) < max(rsi_len, atr_len):
        df = df.copy()
        df["RSI"] = 50.0
        df["ATR"] = 0.0
        df["MCDX_Proxy"] = 0.0
        df["MCDX_Smart"] = 0.0
        df["MCDX_Hot"] = 0.0
        df["MCDX_Retail"] = 100.0
        return df

    df = df.copy()
    
    # Calculate RSI
    df["RSI"] = ta.rsi(df["Close"], length=rsi_len)
    df["RSI"] = df["RSI"].fillna(50.0)
    
    # Calculate ATR
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=atr_len)
    df["ATR"] = df["ATR"].bfill().fillna(0.0)
    
    # Custom Proxy: RSI * ATR
    df["MCDX_Proxy"] = df["RSI"] * df["ATR"]
    
    # Classic MCDX logic (Banker, Hot Money, Retailer)
    # Scale RSI to mimic the typical 3-tier distribution
    rsi_scaled = (df["RSI"] - 30) / (70 - 30) * 100  # Map 30-70 RSI to 0-100
    rsi_scaled = np.clip(rsi_scaled, 0, 100)
    
    # Banker (Smart Money - Red): high volume, strong uptrend
    df["MCDX_Smart"] = np.where(rsi_scaled > 50, (rsi_scaled - 50) * 2, 0)
    # Smooth smart money
    df["MCDX_Smart"] = df["MCDX_Smart"].ewm(span=5, adjust=False).mean()
    
    # Retailer (Green): dominant when trend is weak or downward
    df["MCDX_Retail"] = np.where(rsi_scaled < 50, (50 - rsi_scaled) * 2, 0)
    df["MCDX_Retail"] = df["MCDX_Retail"].ewm(span=5, adjust=False).mean()
    
    # Hot Money (Yellow): mid-level trend presence
    df["MCDX_Hot"] = 100 - df["MCDX_Smart"] - df["MCDX_Retail"]
    df["MCDX_Hot"] = np.clip(df["MCDX_Hot"], 0, 100)
    
    # Re-normalize to ensure they sum to 100%
    total = df["MCDX_Smart"] + df["MCDX_Hot"] + df["MCDX_Retail"]
    df["MCDX_Smart"] = (df["MCDX_Smart"] / total) * 100
    df["MCDX_Hot"] = (df["MCDX_Hot"] / total) * 100
    df["MCDX_Retail"] = (df["MCDX_Retail"] / total) * 100
    
    return df
