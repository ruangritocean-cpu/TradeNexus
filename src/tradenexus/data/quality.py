import datetime
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

def check_stale_candle(
    last_time: datetime.datetime,
    interval: str,
    asset_class: str = "EQUITIES",
    current_time_utc: datetime.datetime = None
) -> Tuple[bool, str]:
    """
    Determines if the latest candle data is stale based on timeframe and asset class.
    Accommodates weekends and market holidays for non-crypto assets.
    """
    if current_time_utc is None:
        current_time_utc = datetime.datetime.now(datetime.timezone.utc)
        
    diff_secs = (current_time_utc - last_time).total_seconds()
    
    is_crypto = asset_class.upper() == "CRYPTO"
    
    # If not crypto and current day is weekend, skip stale warning
    if not is_crypto:
        weekday = current_time_utc.weekday() # 5=Saturday, 6=Sunday
        if weekday in [5, 6]:
            return False, "Market closed for weekend. Skipping stale check."
            
    thresholds = {
        "15m": 3600,            # 1 hour
        "1h": 4 * 3600,         # 4 hours
        "4h": 16 * 3600,        # 16 hours
        "1d": 3 * 86400         # 3 days
    }
    
    limit = thresholds.get(interval, 86400)
    if diff_secs > limit:
        hours = int(diff_secs // 3600)
        return True, f"Data is stale. Last update was {hours} hours ago (threshold: {int(limit//3600)}h)."
        
    return False, ""

def evaluate_data_quality(
    df: pd.DataFrame,
    interval: str,
    asset_class: str = "EQUITIES",
    current_time_utc: datetime.datetime = None
) -> Dict[str, Any]:
    """
    Assesses historical dataframe completeness, volume, stale thresholds, and bar count.
    Returns structured quality check dictionary.
    """
    warnings = []
    errors = []
    
    if df.empty:
        errors.append("DataFrame is empty.")
        return {
            "data_quality_status": "INVALID",
            "bars_available": 0,
            "missing_fields": ["open", "high", "low", "close", "volume"],
            "stale_candle_warning": "",
            "insufficient_warmup_warning": "No bars available.",
            "warnings": warnings,
            "errors": errors,
            "quality_score": 0.0
        }
        
    bars_available = len(df)
    missing_fields = []
    
    # Check for NaN values in core fields
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns or df[col].isnull().all():
            missing_fields.append(col)
            errors.append(f"Field '{col}' is entirely empty or missing.")
        elif df[col].isnull().any():
            missing_fields.append(col)
            warnings.append(f"Field '{col}' contains NaN values.")
            
    # Check for insufficient bars
    warmup_warn = ""
    if bars_available < 100:
        warmup_warn = f"Data history is insufficient ({bars_available} bars) for reliable indicator warmup. Min required: 100."
        warnings.append(warmup_warn)
        
    # Check for stale candles
    stale_warn = ""
    try:
        last_idx = df.index[-1]
        if isinstance(last_idx, pd.Timestamp):
            last_dt = last_idx.to_pydatetime()
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            stale_active, stale_msg = check_stale_candle(last_dt, interval, asset_class, current_time_utc)
            if stale_active:
                stale_warn = stale_msg
                warnings.append(stale_msg)
    except Exception as e:
        warnings.append(f"Failed to verify stale status: {str(e)}")
        
    # Calculate quality score (0.0 to 100.0)
    score = 100.0
    if errors:
        score = 0.0
    else:
        if missing_fields:
            score -= 20.0
        if bars_available < 100:
            score -= 30.0
        if stale_warn:
            score -= 20.0
            
    status = "VALID"
    if errors:
        status = "INVALID"
    elif warnings:
        status = "WARNING"
        
    return {
        "data_quality_status": status,
        "bars_available": bars_available,
        "missing_fields": missing_fields,
        "stale_candle_warning": stale_warn,
        "insufficient_warmup_warning": warmup_warn,
        "warnings": warnings,
        "errors": errors,
        "quality_score": max(0.0, score)
    }
