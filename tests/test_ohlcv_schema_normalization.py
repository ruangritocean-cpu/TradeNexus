import pytest
import pandas as pd
from tradenexus.data.schema import normalize_ohlcv_dataframe

def test_schema_normalization():
    # Construct a raw dataframe with lowercase mixed columns and duplicates
    dates = pd.to_datetime(["2026-07-09 10:00:00", "2026-07-09 09:00:00", "2026-07-09 09:00:00"])
    raw_df = pd.DataFrame({
        "Open": [10.0, 9.0, 9.1],
        "High": [11.0, 10.0, 10.1],
        "Low": [9.0, 8.0, 8.1],
        "Close": [10.5, 9.5, 9.6],
        "Volume": [1000, 2000, 2000]
    }, index=dates)
    
    norm_df = normalize_ohlcv_dataframe(raw_df, "yfinance", "BTC-USD", "1h")
    
    # Assert columns normalized to lowercase
    assert list(norm_df.columns) == [
        "open", "high", "low", "close", "volume", 
        "timestamp", "provider", "symbol", "interval"
    ]
    
    # Assert duplicate index timestamps removed
    assert len(norm_df) == 2
    
    # Assert sorted chronologically ascending
    assert norm_df.index[0] < norm_df.index[1]
    
    # Assert UTC timezone converted
    assert norm_df.index.tz is not None
    assert str(norm_df.index.tz) in ["UTC", "UTC+00:00", "datetime.timezone.utc"]
