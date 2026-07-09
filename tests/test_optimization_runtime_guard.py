import pytest
import time
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from tradenexus.journal.db import init_db
from tradenexus.optimization.optimizer import run_walk_forward_optimization
from tradenexus.optimization.optimization_repository import load_optimization_runs

TEST_DB = "data/test_runtime_opt.sqlite"

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass

@patch("tradenexus.data.providers.fetch_ohlcv_data")
@patch("tradenexus.optimization.optimizer.calculate_volume_indicators")
@patch("tradenexus.optimization.optimizer.calculate_smc_structures")
@patch("tradenexus.optimization.optimizer.calculate_liquidity_zones")
def test_runtime_guard_limit_stop(mock_liq, mock_smc, mock_vol, mock_fetch):
    # Setup mock data for BTC-USD
    dates = pd.date_range("2026-07-01 00:00:00", periods=100, freq="h")
    df_mock = pd.DataFrame({
        "Open": [100.0] * 100,
        "High": [105.0] * 100,
        "Low": [95.0] * 100,
        "Close": [101.0] * 100,
        "Volume": [1000] * 100,
        "CDC_Trend": ["Bullish"] * 100,
        "SuperTrend_Direction": ["Bullish"] * 100,
        "MACD_Trend": ["Bullish"] * 100,
        "Adaptive_Trend": ["Bullish"] * 100,
        "ADX": [30.0] * 100,
        "Support_Level": [95.0] * 100,
        "Support_Source": ["CONFIRMED_SWING"] * 100,
        "Resistance_Level": [105.0] * 100,
        "Resistance_Source": ["CONFIRMED_SWING"] * 100,
        "ATR": [2.0] * 100,
        "primary_regime": ["TRENDING_UP"] * 100,
        "regime_score": [80.0] * 100,
        "regime_flags": [""] * 100
    }, index=dates)
    
    mock_fetch.return_value = (df_mock, "")
    mock_vol.side_effect = lambda df: df
    mock_smc.side_effect = lambda df: df
    mock_liq.side_effect = lambda df: df
    
    # Execute walk-forward run with max_runtime_seconds = -1.0 to force immediate timeout!
    run_id = run_walk_forward_optimization(
        symbol="BTC-USD",
        timeframe="1h",
        start_date="2026-07-01",
        end_date="2026-07-09",
        train_window_bars=10,
        test_window_bars=5,
        step_bars=5,
        max_combinations=5,
        max_runtime_seconds=-1.0,  # Forces timeout immediately
        db_path=TEST_DB
    )
    
    runs = load_optimization_runs(limit=1, db_path=TEST_DB)
    assert len(runs) == 1
    assert runs[0]["status"] == "STOPPED_BY_RUNTIME_LIMIT"
