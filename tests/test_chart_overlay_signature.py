import pytest
import pandas as pd
from unittest.mock import patch
from tradenexus.ui.charts import draw_advanced_charts

def test_chart_overlay_signature_and_missing_columns():
    # Construct minimal test dataframe (empty df triggers immediate warning and return inside draw_advanced_charts)
    # So we provide 10 rows of standard columns
    df = pd.DataFrame({
        "Open": [100.0] * 10,
        "High": [105.0] * 10,
        "Low": [95.0] * 10,
        "Close": [101.0] * 10,
        "Volume": [1000] * 10
    }, index=pd.date_range("2026-07-09 12:00:00", periods=10, freq="1h"))
    
    # We patch st.plotly_chart to avoid calling Streamlit components under pytest
    with patch("streamlit.plotly_chart") as mock_chart:
        # 1. Verify accepting all keyword arguments
        draw_advanced_charts(
            df=df,
            ticker="AAPL",
            timeframe="1h",
            show_vwap=True,
            show_fvg=True,
            show_ob=True,
            show_sweeps=True,
            show_bos_choch=True,
            show_eql_eqh=True,
            show_market_regime_shading=True
        )
        
        # 2. Verify backward compatible alias parameters
        draw_advanced_charts(
            df=df,
            ticker="AAPL",
            timeframe="1h",
            show_equal_highs_lows=True,
            show_regime=True
        )
        
        # 3. Verify tf parameter compatibility
        draw_advanced_charts(
            df=df,
            ticker="AAPL",
            tf="1h"
        )
        
        assert mock_chart.call_count == 3

def test_toggles_with_columns_exist():
    # Construct test dataframe with all indicator columns
    df = pd.DataFrame({
        "Open": [100.0] * 10,
        "High": [105.0] * 10,
        "Low": [95.0] * 10,
        "Close": [101.0] * 10,
        "Volume": [1000] * 10,
        "primary_regime": ["SIDEWAYS"] * 10,
        "BOS_Present": [1] * 10,
        "CHOCH_Present": [1] * 10,
        "Equal_Highs": [1] * 10,
        "Equal_Lows": [1] * 10,
        "Swing_High": [105.0] * 10,
        "Swing_Low": [95.0] * 10,
        "Liquidity_Sweep": [1] * 10,
        "Sweep_Direction": ["BULLISH"] * 10
    }, index=pd.date_range("2026-07-09 12:00:00", periods=10, freq="1h"))
    
    with patch("streamlit.plotly_chart") as mock_chart:
        draw_advanced_charts(
            df=df,
            ticker="AAPL",
            timeframe="1h",
            show_bos_choch=True,
            show_eql_eqh=True,
            show_market_regime_shading=True
        )
        
        assert mock_chart.called
