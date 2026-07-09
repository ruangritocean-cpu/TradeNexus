import yfinance as yf
import pandas as pd
import logging
from tradenexus.data.cache import global_cache, get_interval_ttl

logger = logging.getLogger(__name__)

def fetch_ohlcv_data(ticker: str, interval: str = "15m", period: str = None) -> tuple[pd.DataFrame, str]:
    """
    Fetches native OHLCV data from Yahoo Finance for a given ticker and interval.
    Uses TTLCache to prevent repeated requests during rerun cycles.
    
    Args:
        ticker (str): The financial instrument symbol (e.g., BTC-USD, AAPL).
        interval (str): Base timeframe ('15m', '1h', '1d').
        period (str, optional): Overrides the default historical lookup period.
        
    Returns:
        tuple[pd.DataFrame, str]: (Cleaned OHLCV DataFrame, Quality warning message if any)
    """
    # Map interval to appropriate periods that ensure fast load while keeping enough warmup history
    interval_period_map = {
        "15m": "14d",
        "1h": "60d",
        "1d": "365d",
    }
    
    if not period:
        period = interval_period_map.get(interval, "60d")
        
    cache_key = f"ohlcv_{ticker}_{interval}_{period}"
    cached_val = global_cache.get(cache_key)
    if cached_val is not None:
        logger.debug(f"Retrieved cached OHLCV data for {ticker} ({interval}, {period})")
        return cached_val[0].copy(), cached_val[1]
        
    logger.info(f"Fetching native {ticker} data with interval={interval}, period={period}")
    warning_msg = ""
    
    try:
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )
        
        if df.empty:
            logger.warning(f"No data returned for ticker {ticker} with interval {interval}.")
            res = (pd.DataFrame(), f"No data returned for ticker {ticker} with interval {interval}.")
            global_cache.set(cache_key, res, get_interval_ttl(interval))
            return res
            
        # Clean column names (yfinance can return MultiIndex columns in newer versions)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Standardize columns to capitalized Case
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        available_cols = [c for c in required_cols if c in df.columns]
        
        df = df[available_cols].copy()
        
        # Ensure we have all required columns
        for col in required_cols:
            if col not in df.columns:
                err_msg = f"Missing column {col} in fetched data."
                logger.error(err_msg)
                return pd.DataFrame(), err_msg
                
        # Drop rows with NaN in OHLCV
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        
        # Sort index just in case
        df = df.sort_index()
        
        # Check warmup quality (e.g. need at least 100 candles for solid indicators)
        if len(df) < 100:
            warning_msg = f"Data history is insufficient ({len(df)} bars) for reliable indicator warmup. Min required: 100."
            logger.warning(f"Quality Check Warning for {ticker} ({interval}): {warning_msg}")
            
        logger.info(f"Successfully fetched {len(df)} rows for {ticker} ({interval}).")
        res = (df, warning_msg)
        global_cache.set(cache_key, res, get_interval_ttl(interval))
        return df.copy(), warning_msg
        
    except Exception as e:
        err_msg = f"Error fetching data for ticker {ticker}: {str(e)}"
        logger.error(err_msg)
        return pd.DataFrame(), err_msg
