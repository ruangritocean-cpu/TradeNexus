import pytest
import pandas as pd
from tradenexus.indicators.structure import calculate_smc_structures
from tradenexus.indicators.liquidity import calculate_liquidity_zones

def test_fvg_detection():
    """
    Verifies that FVG (Fair Value Gap) is detected correctly.
    """
    df = pd.DataFrame({
        "High": [10.0, 11.0, 15.0],
        "Low": [8.0, 9.0, 12.0],  # Low[2] (12.0) > High[0] (10.0) -> Bullish FVG
        "Close": [9.0, 10.0, 14.0],
        "Open": [9.5, 9.5, 10.5]
    })
    
    df_calc = calculate_smc_structures(df)
    assert df_calc.iloc[2]["FVG_Present"] == 1
    assert df_calc.iloc[2]["FVG_Direction"] == "BULLISH"

def test_liquidity_sweep():
    """
    Verifies that Liquidity Sweep occurs when price breaches but closes within structural limits.
    """
    df = pd.DataFrame({
        "High": [10.0, 12.0, 10.0],
        "Low": [8.0, 7.5, 8.5],
        "Close": [9.0, 9.5, 9.0],
        "Support_Level": [8.0, 8.0, 8.0],
        "Resistance_Level": [11.0, 11.0, 11.0],
        "Swing_High": [None, None, None],
        "Swing_Low": [None, None, None]
    })
    
    df_calc = calculate_liquidity_zones(df)
    # High[1] (12.0) swept Resistance_Level (11.0) but Close[1] (9.5) closed below 11.0 -> Bearish Sweep
    assert df_calc.iloc[1]["Liquidity_Sweep"] == 1
    assert df_calc.iloc[1]["Sweep_Direction"] == "BEARISH"
