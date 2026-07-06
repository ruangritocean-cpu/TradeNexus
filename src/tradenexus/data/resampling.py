import pandas as pd
import logging

logger = logging.getLogger(__name__)

def resample_timeframe(df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """
    Resamples base OHLCV data into a higher target timeframe.
    Typically used to resample native 1H data into 4H candles.
    
    Args:
        df (pd.DataFrame): Base timeframe OHLCV data.
        target_tf (str): Target timeframe string (e.g., '4h').
        
    Returns:
        pd.DataFrame: Resampled OHLCV data.
    """
    if df.empty:
        return pd.DataFrame()
        
    # Map friendly names to pandas offset aliases
    tf_map = {
        "4h": "4h",
    }
    
    rule = tf_map.get(target_tf, target_tf)
    
    try:
        agg_dict = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }
        
        # Resample and drop NaN intervals
        resampled_df = df.resample(rule).agg(agg_dict).dropna(subset=["Open", "High", "Low", "Close"])
        
        logger.info(f"Resampled data from base shape {df.shape} to {target_tf} shape {resampled_df.shape}")
        return resampled_df
        
    except Exception as e:
        logger.error(f"Error resampling to timeframe {target_tf}: {str(e)}")
        return pd.DataFrame()
