import pytest
import pandas as pd
import numpy as np

from tradenexus.indicators.trend import calculate_cdc_actionzone, calculate_adaptive_trend
from tradenexus.indicators.momentum import calculate_macd, calculate_adx
from tradenexus.indicators.volatility import calculate_bollinger_bands

def test_indicator_stability():
    """
    Verifies that historical calculated values for CDC, KAMA, MACD, 
    ADX, and Bollinger Bands do not shift or change when new candles 
    are appended in the future (stability guarantee).
    """
    np.random.seed(100)
    periods = 150
    dates = pd.date_range(start="2026-01-01", periods=periods, freq="15min")
    prices = 50000.0 + np.cumsum(np.random.randn(periods) * 100.0)
    
    df_full = pd.DataFrame({
        "Open": prices - 50.0,
        "High": prices + 100.0,
        "Low": prices - 100.0,
        "Close": prices,
        "Volume": 5.0
    }, index=dates)
    
    slice_len = 100
    df_sliced = df_full.iloc[:slice_len].copy()
    
    # Calculate indicators on sliced data
    s_calc = df_sliced.copy()
    s_calc = calculate_cdc_actionzone(s_calc)
    s_calc = calculate_macd(s_calc)
    s_calc = calculate_adaptive_trend(s_calc)
    s_calc = calculate_bollinger_bands(s_calc)
    s_calc = calculate_adx(s_calc)
    
    # Calculate indicators on full data
    f_calc = df_full.copy()
    f_calc = calculate_cdc_actionzone(f_calc)
    f_calc = calculate_macd(f_calc)
    f_calc = calculate_adaptive_trend(f_calc)
    f_calc = calculate_bollinger_bands(f_calc)
    f_calc = calculate_adx(f_calc)
    
    # Check historical values at the boundary (index slice_len - 1)
    for col in ["EMA_Fast", "EMA_Slow", "CDC_Trend", "KAMA", "Adaptive_Trend", "MACD", "MACD_Signal", "BBU", "BBL", "ADX"]:
        assert s_calc.iloc[slice_len - 1][col] == f_calc.iloc[slice_len - 1][col], f"Indicator column {col} changed value!"
        
    # Check whole historical series match exactly
    for col in ["EMA_Fast", "EMA_Slow", "KAMA", "MACD", "MACD_Signal", "BBU", "BBL", "BBM", "ADX"]:
        pd.testing.assert_series_equal(
            s_calc[col],
            f_calc[col].iloc[:slice_len],
            obj=f"Stability check for {col}"
        )
