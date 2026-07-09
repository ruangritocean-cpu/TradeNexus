import logging
import pandas as pd
from typing import Dict
from tradenexus.data.providers import fetch_ohlcv_data
from tradenexus.data.resampling import resample_timeframe

logger = logging.getLogger(__name__)

def fetch_and_resample_mtf_data(symbol: str) -> Dict[str, pd.DataFrame]:
    """
    Fetches base timeframes (15m, 1h, 1d) from yfinance and resamples 1h to 4h.
    Validates that returned data is non-empty.
    """
    df_15m, w_15m = fetch_ohlcv_data(symbol, interval="15m")
    df_1h, w_1h = fetch_ohlcv_data(symbol, interval="1h")
    df_1d, w_1d = fetch_ohlcv_data(symbol, interval="1d")
    
    if df_15m.empty or df_1h.empty or df_1d.empty:
        raise ValueError("Incomplete historical data fetched from data providers.")
        
    df_4h = resample_timeframe(df_1h, "4h")
    
    return {
        "15m": df_15m,
        "1h": df_1h,
        "4h": df_4h,
        "1d": df_1d
    }
