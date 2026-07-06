import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import logging

logger = logging.getLogger(__name__)

def calculate_bollinger_bands(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Bollinger Bands and Squeeze Alert.
    """
    df = df.copy()
    if len(df) < length:
        df["BBL"] = np.nan
        df["BBM"] = np.nan
        df["BBU"] = np.nan
        df["BB_Bandwidth"] = np.nan
        df["BB_Squeeze"] = False
        return df

    bb_df = ta.bbands(df["Close"], length=length, std=std)
    if bb_df is not None and not bb_df.empty:
        df["BBL"] = bb_df.iloc[:, 0]
        df["BBM"] = bb_df.iloc[:, 1]
        df["BBU"] = bb_df.iloc[:, 2]
        df["BB_Bandwidth"] = bb_df.iloc[:, 3]
    else:
        df["BBM"] = df["Close"].rolling(window=length).mean()
        rolling_std = df["Close"].rolling(window=length).std()
        df["BBU"] = df["BBM"] + (std * rolling_std)
        df["BBL"] = df["BBM"] - (std * rolling_std)
        df["BB_Bandwidth"] = (df["BBU"] - df["BBL"]) / df["BBM"]

    bw = df["BB_Bandwidth"]
    if len(df) >= 100:
        bandwidth_quantile = bw.rolling(window=100).quantile(0.20)
        df["BB_Squeeze"] = bw < bandwidth_quantile
    else:
        df["BB_Squeeze"] = False
        
    df["BB_Squeeze"] = df["BB_Squeeze"].fillna(False)
    return df
