import time
import pandas as pd
import logging
from typing import List, Optional, Dict, Any, Tuple
import datetime

from tradenexus.data.provider_interface import DataProvider
from tradenexus.data.provider_registry import get_provider, get_fallback_chain
from tradenexus.data.provider_health import record_success, record_failure
from tradenexus.data.quality import evaluate_data_quality

logger = logging.getLogger(__name__)

def execute_fallback_chain(
    symbol: str,
    interval: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    asset_class: str = "EQUITIES",
    current_time_utc: datetime.datetime = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Tries fetching data sequentially from registered providers based on fallback order.
    Determines provider suitability using health state and data quality scoring.
    Returns:
        tuple: (normalized DataFrame, quality report dictionary)
    """
    fallback_chain = get_fallback_chain()
    if not fallback_chain:
        logger.error("No data providers registered in the registry.")
        raise RuntimeError("No data providers registered in the registry.")
        
    last_error_msg = ""
    fallback_used = False
    
    for idx, provider_name in enumerate(fallback_chain):
        if idx > 0:
            fallback_used = True
            logger.info(f"Fallback active: attempting secondary provider '{provider_name}' for {symbol} ({interval})")
            
        try:
            provider = get_provider(provider_name)
        except Exception as e:
            logger.warning(f"Skipping unregistered fallback provider '{provider_name}': {str(e)}")
            continue
            
        start_time = time.perf_counter()
        
        try:
            df = provider.fetch_ohlcv(symbol, interval, period, start, end)
            duration = time.perf_counter() - start_time
            
            # Evaluate Data Quality
            quality_report = evaluate_data_quality(df, interval, asset_class, current_time_utc)
            
            if quality_report["data_quality_status"] == "INVALID":
                logger.warning(f"Provider '{provider_name}' returned INVALID quality data. Errors: {quality_report['errors']}")
                record_failure(provider_name)
                last_error_msg = f"'{provider_name}' INVALID data: " + ", ".join(quality_report["errors"])
                continue
                
            # If healthy, record success
            record_success(provider_name, duration)
            
            # Populate fallback indicator flag inside quality report
            quality_report["provider_used"] = provider_name
            quality_report["fallback_used"] = 1 if fallback_used else 0
            
            # Add DatetimeIndex conversion back to normalized DataFrame to assist Plotly index mapping
            if not df.empty and "timestamp" in df.columns:
                df.index = pd.to_datetime(df["timestamp"])
                
            return df, quality_report
            
        except Exception as ex:
            record_failure(provider_name)
            last_error_msg = f"'{provider_name}' execution error: {str(ex)}"
            logger.error(f"Failed to fetch data from provider '{provider_name}': {str(ex)}")
            
    # If all providers fail, return empty dataframe and INVALID report
    logger.critical(f"All data providers failed to retrieve {symbol}. Last error: {last_error_msg}")
    
    empty_report = {
        "data_quality_status": "INVALID",
        "bars_available": 0,
        "missing_fields": ["open", "high", "low", "close", "volume"],
        "stale_candle_warning": "",
        "insufficient_warmup_warning": "All providers failed.",
        "provider_used": "NONE",
        "fallback_used": 0,
        "warnings": [],
        "errors": [f"All data providers failed. Last error: {last_error_msg}"],
        "quality_score": 0.0
    }
    
    return pd.DataFrame(), empty_report
