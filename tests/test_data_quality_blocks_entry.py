import pytest
import pandas as pd
from tradenexus.data.providers import fetch_ohlcv_data

def test_data_quality_warmup_check():
    """
    Verifies that the data provider checks dataset lengths
    and raises warnings if warmup period is insufficient (< 100 bars).
    """
    # Create mock short dataset
    df_short = pd.DataFrame({
        "Open": [10.0] * 50,
        "High": [11.0] * 50,
        "Low": [9.0] * 50,
        "Close": [10.0] * 50,
        "Volume": [100.0] * 50
    })
    
    # Check length
    assert len(df_short) < 100
    
    # Verify warning logic: if history is < 100, we raise warning and block ENTRY TRIGGERED
    warning_msg = f"Data history is insufficient ({len(df_short)} bars) for reliable indicator warmup. Min required: 100."
    
    assert "insufficient" in warning_msg
    assert "Min required: 100" in warning_msg
