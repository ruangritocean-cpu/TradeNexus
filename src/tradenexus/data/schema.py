import pandas as pd
import numpy as np

def normalize_ohlcv_dataframe(
    df: pd.DataFrame,
    provider_name: str,
    symbol: str,
    interval: str
) -> pd.DataFrame:
    """
    Standardizes a provider's raw dataframe to the normalized TradeNexus lowercase schema.
    Enforces UTC timezone index, sorted order, duplicate removal, and missing volume handling.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "open", "high", "low", "close", "volume", 
            "timestamp", "provider", "symbol", "interval"
        ])
        
    df_clean = df.copy()
    
    # Handle multi-level columns if any
    if isinstance(df_clean.columns, pd.MultiIndex):
        df_clean.columns = df_clean.columns.get_level_values(0)
        
    # Mapping table (case-insensitive conversion to lowercase columns)
    column_mapping = {}
    for col in df_clean.columns:
        col_lower = str(col).lower()
        if col_lower in ["open", "high", "low", "close", "volume"]:
            column_mapping[col] = col_lower
            
    df_clean = df_clean.rename(columns=column_mapping)
    
    # Verify required OHLC columns exist
    required = ["open", "high", "low", "close"]
    for req in required:
        if req not in df_clean.columns:
            # Create NaN column if missing
            df_clean[req] = np.nan
            
    if "volume" not in df_clean.columns:
        df_clean["volume"] = 0.0
    else:
        df_clean["volume"] = df_clean["volume"].fillna(0.0)
        
    # Ensure Index is DatetimeIndex and timezone-aware UTC
    if not isinstance(df_clean.index, pd.DatetimeIndex):
        if "timestamp" in df_clean.columns:
            df_clean.index = pd.to_datetime(df_clean["timestamp"])
        elif "date" in df_clean.columns:
            df_clean.index = pd.to_datetime(df_clean["date"])
        else:
            # Fallback to standard range
            df_clean.index = pd.to_datetime(df_clean.index)
            
    # Normalize Timezone to UTC
    if df_clean.index.tz is None:
        df_clean.index = df_clean.index.tz_localize("UTC")
    else:
        df_clean.index = df_clean.index.tz_convert("UTC")
        
    # Remove duplicate index timestamps, keep first occurrence
    df_clean = df_clean[~df_clean.index.duplicated(keep="first")]
    
    # Sort chronological ascending
    df_clean = df_clean.sort_index()
    
    # Reset index to populate 'timestamp' column as ISO string
    df_clean["timestamp"] = df_clean.index.map(lambda x: x.isoformat())
    df_clean["provider"] = provider_name
    df_clean["symbol"] = symbol
    df_clean["interval"] = interval
    
    # Keep only standardized fields
    final_cols = [
        "open", "high", "low", "close", "volume", 
        "timestamp", "provider", "symbol", "interval"
    ]
    
    # Convert data types safely
    for col in ["open", "high", "low", "close", "volume"]:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
        
    return df_clean[final_cols]
