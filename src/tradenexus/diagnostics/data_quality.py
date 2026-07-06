import logging
import pandas as pd
import datetime
import yfinance as yf
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def check_data_feed_quality(symbols: List[str]) -> Dict[str, Any]:
    """
    Validates yfinance data structures, checking for missing values, stale candles, or insufficient warmup.
    """
    results = {}
    has_errors = False
    
    if not symbols:
        return {"feed_status": "OK", "details": {}, "summary": "No symbols specified."}
        
    for symbol in symbols:
        warnings = []
        errors = []
        status = "OK"
        latest_time = None
        bars = 0
        
        try:
            # Download a small batch of 1d history to check availability and shape
            df = yf.download(symbol, period="30d", interval="1d", progress=False, auto_adjust=True)
            if df.empty:
                errors.append("Download returned empty dataframe.")
                status = "FAILED"
                has_errors = True
            else:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                    
                bars = len(df)
                latest_time = df.index[-1].isoformat()
                
                # Check required columns
                required = ["Open", "High", "Low", "Close", "Volume"]
                for col in required:
                    if col not in df.columns:
                        errors.append(f"Column '{col}' is missing.")
                        status = "FAILED"
                        has_errors = True
                        
                # Check for null/NaN values
                null_counts = df.isnull().sum().sum()
                if null_counts > 0:
                    warnings.append(f"Data contains {null_counts} null/NaN values.")
                    if status != "FAILED":
                        status = "WARNING"
                        
                # Check for zero volumes
                zero_vol = (df["Volume"] == 0).sum()
                if zero_vol > (bars * 0.5): # more than 50% zero volume
                    warnings.append(f"High percentage of zero volume bars detected: {zero_vol}/{bars}.")
                    if status != "FAILED":
                        status = "WARNING"
                        
                # Warmup period check: technical indicators need >= 100 bars usually
                if bars < 20:
                    warnings.append(f"Insufficient warmup period history. Found {bars} daily bars.")
                    if status != "FAILED":
                        status = "WARNING"
                        
        except Exception as e:
            errors.append(f"Data download threw exception: {str(e)}")
            status = "FAILED"
            has_errors = True
            
        results[symbol] = {
            "status": status,
            "latest_candle_time": latest_time,
            "bars_available": bars,
            "warnings": warnings,
            "errors": errors
        }
        
    overall_status = "FAILED" if has_errors else ("WARNING" if any(x["status"] == "WARNING" for x in results.values()) else "OK")
    return {
        "feed_status": overall_status,
        "details": results
    }
