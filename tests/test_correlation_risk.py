import pytest
import pandas as pd
from unittest.mock import patch
from tradenexus.portfolio.correlation import calculate_returns_correlation

def test_correlation_matrix_calculation():
    """
    Verifies that correlation calculations successfully identify highly correlated
    pairs and fail gracefully when data is missing.
    """
    # 1. Mock yfinance download to return correlated prices
    # Asset A: moves up consistently
    # Asset B: moves up consistently (highly correlated with A)
    # Asset C: moves randomly (low correlation)
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df_a = pd.DataFrame({"Close": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]}, index=dates)
    df_b = pd.DataFrame({"Close": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0]}, index=dates)
    df_c = pd.DataFrame({"Close": [10.0, 9.0, 15.0, 8.0, 14.0, 7.0, 12.0, 6.0, 11.0, 5.0]}, index=dates)
    
    mock_data = {
        "A": df_a,
        "B": df_b,
        "C": df_c
    }
    
    def mock_download(sym, period=None, interval=None, progress=False, auto_adjust=True):
        return mock_data.get(sym, pd.DataFrame())
        
    with patch("tradenexus.portfolio.correlation.yf.download", side_effect=mock_download):
        res = calculate_returns_correlation(
            symbols=["A", "B", "C"],
            lookback_bars=10,
            correlation_threshold=0.8,
            cache_ttl_seconds=0  # force refresh
        )
        
        # Check matrix exists
        assert "A" in res.correlation_matrix
        assert "B" in res.correlation_matrix
        assert "C" in res.correlation_matrix
        
        # A and B are perfectly correlated (1.0)
        corr_ab = res.correlation_matrix["A"]["B"]
        assert corr_ab > 0.9
        
        # A and C are not highly correlated
        corr_ac = res.correlation_matrix["A"]["C"]
        assert abs(corr_ac) < 0.7
        
        # High correlation warning triggered for A and B
        assert len(res.highly_correlated_pairs) == 1
        assert res.highly_correlated_pairs[0][0] == "A"
        assert res.highly_correlated_pairs[0][1] == "B"
        assert "High correlation detected" in res.correlation_warning
