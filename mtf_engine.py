import pandas as pd
import logging

logger = logging.getLogger(__name__)

def resample_timeframe(df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """
    Resamples base OHLCV data into a higher target timeframe.
    
    Args:
        df (pd.DataFrame): Base timeframe OHLCV data.
        target_tf (str): Target timeframe string (e.g., '1h', '4h', '1d').
        
    Returns:
        pd.DataFrame: Resampled OHLCV data.
    """
    if df.empty:
        return pd.DataFrame()
        
    # Map friendly names to pandas offset aliases
    tf_map = {
        "15m": "15min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D"
    }
    
    rule = tf_map.get(target_tf, target_tf)
    
    try:
        # Aggregate logic
        agg_dict = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }
        
        # We want to resample, aggregate, and drop any intervals that ended up with NaN
        # (e.g., non-trading hours if we resample stock data).
        resampled_df = df.resample(rule).agg(agg_dict).dropna(subset=["Open", "High", "Low", "Close"])
        
        logger.info(f"Resampled data from base shape {df.shape} to {target_tf} shape {resampled_df.shape}")
        return resampled_df
        
    except Exception as e:
        logger.error(f"Error resampling to timeframe {target_tf}: {str(e)}")
        return pd.DataFrame()
