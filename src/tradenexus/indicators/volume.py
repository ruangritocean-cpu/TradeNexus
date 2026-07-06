import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_volume_indicators(df: pd.DataFrame, mfi_period: int = 14, cmf_period: int = 20) -> pd.DataFrame:
    """
    Calculates Volume and Money Flow Indicators: VWAP, OBV, MFI, CMF.
    
    Robustness:
    If volume is missing, zero, or constant, does not crash and fills
    indicators with neutral values.
    """
    df = df.copy()
    
    # Check volume quality
    has_valid_volume = True
    if "Volume" not in df.columns or df["Volume"].isna().all() or df["Volume"].sum() == 0:
        has_valid_volume = False
        
    if not has_valid_volume:
        # Fill with neutral values
        df["VWAP"] = df["Close"]
        df["OBV"] = 0.0
        df["MFI"] = 50.0
        df["CMF"] = 0.0
        df["Volume_Confirmation"] = "NEUTRAL"
        df["Volume_Warning"] = "Volume data unavailable or unreliable"
        return df

    df["Volume_Warning"] = ""
    
    # 1. VWAP (Intraday cumulative reset based on date)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    tp_vol = typical_price * df["Volume"]
    
    # Group by date for intraday reset
    dates = pd.Series(df.index.date, index=df.index)
    cum_tp_vol = tp_vol.groupby(dates).cumsum()
    cum_vol = df["Volume"].groupby(dates).cumsum()
    
    df["VWAP"] = cum_tp_vol / cum_vol
    # Fill any NaNs in VWAP with close price
    df["VWAP"] = df["VWAP"].fillna(df["Close"])
    
    # 2. OBV
    close_diff = df["Close"].diff()
    direction = np.where(close_diff > 0, 1, np.where(close_diff < 0, -1, 0))
    obv_val = (direction * df["Volume"]).cumsum()
    df["OBV"] = obv_val
    
    # 3. Money Flow Index (MFI)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    raw_money_flow = typical_price * df["Volume"]
    
    tp_diff = typical_price.diff()
    pos_flow = np.where(tp_diff > 0, raw_money_flow, 0.0)
    neg_flow = np.where(tp_diff < 0, raw_money_flow, 0.0)
    
    pos_flow_sum = pd.Series(pos_flow, index=df.index).rolling(window=mfi_period).sum()
    neg_flow_sum = pd.Series(neg_flow, index=df.index).rolling(window=mfi_period).sum()
    
    # Handle division by zero
    mr = pos_flow_sum / neg_flow_sum
    mfi = 100.0 - (100.0 / (1.0 + mr))
    
    # If neg_flow_sum is zero, MFI is 100 if pos_flow_sum > 0, else 50
    mfi = np.where(neg_flow_sum == 0, np.where(pos_flow_sum > 0, 100.0, 50.0), mfi)
    df["MFI"] = mfi
    df["MFI"] = df["MFI"].fillna(50.0)
    
    # 4. Chaikin Money Flow (CMF)
    denom = df["High"] - df["Low"]
    # If High == Low, multiplier is 0
    multiplier = np.where(denom == 0, 0.0, ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / denom)
    mf_vol = multiplier * df["Volume"]
    
    mf_vol_sum = mf_vol.rolling(window=cmf_period).sum()
    vol_sum = df["Volume"].rolling(window=cmf_period).sum()
    
    cmf = mf_vol_sum / vol_sum
    cmf = np.where(vol_sum == 0, 0.0, cmf)
    df["CMF"] = cmf
    df["CMF"] = df["CMF"].fillna(0.0)
    
    # 5. Volume Confirmation State
    # Determine confirmation based on: CMF > 0 (bullish) or CMF < 0 (bearish)
    # and agreement with MFI (> 50 / < 50)
    # VWAP alignment is handled separately
    df["Volume_Confirmation"] = "NEUTRAL"
    
    # Let's say:
    # Bullish confirmation: CMF > 0.05 and MFI > 50
    # Bearish confirmation: CMF < -0.05 and MFI < 50
    mfi_bull = df["MFI"] > 50
    cmf_bull = df["CMF"] > 0.05
    mfi_bear = df["MFI"] < 50
    cmf_bear = df["CMF"] < -0.05
    
    df.loc[mfi_bull & cmf_bull, "Volume_Confirmation"] = "BULLISH"
    df.loc[mfi_bear & cmf_bear, "Volume_Confirmation"] = "BEARISH"
    
    return df
