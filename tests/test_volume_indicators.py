import pytest
import pandas as pd
import numpy as np
from tradenexus.indicators.volume import calculate_volume_indicators

def test_volume_indicators_standard():
    """
    Verifies that volume indicators (VWAP, OBV, MFI, CMF) calculate correctly
    using standard mock data with volume.
    """
    dates = pd.date_range("2026-01-01 09:30:00", periods=20, freq="15min")
    df = pd.DataFrame({
        "Open": [10.0] * 20,
        "High": [12.0] * 20,
        "Low": [8.0] * 20,
        "Close": [11.0] * 20,
        "Volume": [1000.0] * 20
    }, index=dates)
    
    # Close price rises on day 2 or row 5
    df.iloc[5, df.columns.get_loc("Close")] = 13.0
    
    df_calc = calculate_volume_indicators(df, mfi_period=5, cmf_period=5)
    
    assert "VWAP" in df_calc.columns
    assert "OBV" in df_calc.columns
    assert "MFI" in df_calc.columns
    assert "CMF" in df_calc.columns
    
    # OBV should increase after price rises
    assert df_calc.iloc[5]["OBV"] > 0
    
    # MFI bounds check
    assert (df_calc["MFI"] >= 0).all() and (df_calc["MFI"] <= 100).all()

def test_missing_volume_handling():
    """
    Verifies that the calculator handles missing or empty volume gracefully.
    """
    dates = pd.date_range("2026-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        "Open": [10.0] * 20,
        "High": [12.0] * 20,
        "Low": [8.0] * 20,
        "Close": [11.0] * 20,
        "Volume": [0.0] * 20  # Constant zero volume
    }, index=dates)
    
    df_calc = calculate_volume_indicators(df)
    
    # Values should fall back to neutral without throwing error
    assert (df_calc["VWAP"] == df_calc["Close"]).all()
    assert (df_calc["OBV"] == 0.0).all()
    assert (df_calc["MFI"] == 50.0).all()
    assert (df_calc["CMF"] == 0.0).all()
    assert (df_calc["Volume_Confirmation"] == "NEUTRAL").all()
    assert "unavailable" in df_calc.iloc[0]["Volume_Warning"]
