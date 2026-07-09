import yfinance as yf
import pandas as pd
import logging
from typing import List, Optional
from tradenexus.data.provider_interface import DataProvider
from tradenexus.data.schema import normalize_ohlcv_dataframe

logger = logging.getLogger(__name__)

class YFinanceDataProvider(DataProvider):
    """
    DataProvider wrapper for Yahoo Finance (yfinance).
    """
    @property
    def provider_name(self) -> str:
        return "yfinance"

    @property
    def supported_intervals(self) -> List[str]:
        return ["15m", "1h", "4h", "1d"]

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        period: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        # Standardize period map
        interval_period_map = {
            "15m": "14d",
            "1h": "60d",
            "4h": "60d",
            "1d": "365d",
        }
        
        if not period and not start:
            period = interval_period_map.get(interval, "60d")
            
        logger.info(f"YFinanceDataProvider: downloading {symbol} with interval={interval}, period={period}, start={start}, end={end}")
        
        # Determine parameters
        kwargs = {
            "tickers": symbol,
            "interval": "1h" if interval == "4h" else interval, # yfinance does not support native 4h
            "progress": False,
            "auto_adjust": True
        }
        
        if start:
            kwargs["start"] = start
            if end:
                kwargs["end"] = end
        else:
            kwargs["period"] = period
            
        try:
            df = yf.download(**kwargs)
            if df.empty:
                logger.warning(f"YFinanceDataProvider: empty data returned for {symbol}")
                return pd.DataFrame()
                
            # If 4h resample is requested, resample the 1h data
            if interval == "4h":
                from tradenexus.data.resampling import resample_timeframe
                df = resample_timeframe(df, "4h")
                
            # Normalize schema
            df_norm = normalize_ohlcv_dataframe(df, self.provider_name, symbol, interval)
            return df_norm
            
        except Exception as e:
            logger.error(f"YFinanceDataProvider: error during download: {str(e)}")
            return pd.DataFrame()

    def health_check(self) -> bool:
        """
        Check connectivity by attempting to download a tiny set of SPY index data.
        """
        try:
            df = yf.download(tickers="SPY", period="1d", interval="1d", progress=False)
            return not df.empty
        except Exception:
            return False
