import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_ohlcv_data(ticker: str, interval: str = "15m") -> pd.DataFrame:
    """
    Fetches OHLCV data from Yahoo Finance for a given ticker and interval.
    Respects yfinance limits on historical periods for intraday data:
    - 15m: max 60 days
    - 1h: max 730 days
    - 1d: max 10 years (or more)
    
    Args:
        ticker (str): The financial instrument symbol (e.g., BTC-USD, AAPL).
        interval (str): Base timeframe ('15m', '1h', '1d').
        
    Returns:
        pd.DataFrame: Cleaned OHLCV data with Datetime index.
    """
    # Map interval to maximum allowed or appropriate periods
    interval_period_map = {
        "15m": "60d",
        "1h": "730d",
        "1d": "2y",  # Fetch 2 years of daily data by default
    }
    
    period = interval_period_map.get(interval, "60d")
    
    logger.info(f"Fetching {ticker} data with interval={interval}, period={period}")
    
    try:
        # Download data
        df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )
        
        if df.empty:
            logger.warning(f"No data returned for ticker {ticker} with interval {interval}.")
            return pd.DataFrame()
            
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
                logger.error(f"Missing column {col} in fetched data.")
                return pd.DataFrame()
                
        # Drop rows with NaN in OHLCV
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        
        # Sort index just in case
        df = df.sort_index()
        
        logger.info(f"Successfully fetched {len(df)} rows for {ticker}.")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for ticker {ticker}: {str(e)}")
        return pd.DataFrame()
