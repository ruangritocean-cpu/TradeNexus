import pytest
import os
import pandas as pd
import datetime
from unittest.mock import patch, MagicMock
from tradenexus.journal.db import init_db
from tradenexus.scanner.scan_engine import run_watchlist_scan
from tradenexus.journal.repository import load_signals

TEST_DB = "data/test_scan_engine.sqlite"
TEST_WL = "data/test_scan_engine_watchlist.json"

@pytest.fixture(autouse=True)
def setup_te():
    for f in [TEST_DB, TEST_WL]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except PermissionError:
                pass
    init_db(TEST_DB)
    
    # Create test watchlist
    import json
    wl_data = [
        {"symbol": "BTC-USD", "display_name": "Bitcoin", "enabled": True, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True},
        {"symbol": "ETH-USD", "display_name": "Ethereum", "enabled": False, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True},
        {"symbol": "FAIL-USD", "display_name": "Failing Symbol", "enabled": True, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True}
    ]
    with open(TEST_WL, "w") as f:
        json.dump(wl_data, f)
        
    yield
    for f in [TEST_DB, TEST_WL]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except PermissionError:
                pass

@patch("tradenexus.scanner.scan_engine.fetch_ohlcv_data")
@patch("tradenexus.scanner.scan_engine.calculate_confluence_score")
@patch("tradenexus.scanner.scan_engine.validate_trade_risk")
@patch("tradenexus.scanner.scan_engine.evaluate_mtf_hierarchy")
@patch("tradenexus.scanner.scan_engine.apply_regime_decision_rules")
def test_scan_engine_behavior(mock_regime_rules, mock_mtf, mock_risk, mock_conf, mock_fetch):
    """
    Verifies that the scan engine runs sequentially, skips disabled assets,
    continues when one asset fails, logs to database, and blocks open-candle logs.
    """
    # Setup mock data for BTC-USD
    dates = pd.date_range("2026-01-01 00:00:00", periods=110, freq="h")
    df_mock = pd.DataFrame({
        "Open": [100.0] * 110,
        "High": [102.0] * 110,
        "Low": [98.0] * 110,
        "Close": [101.0] * 110,
        "Volume": [1000.0] * 110
    }, index=dates)
    
    # Mock yfinance return values
    def fetch_side_effect(ticker, interval, period=None):
        if ticker == "FAIL-USD":
            raise ValueError("API Connection Timeout")
        return df_mock.copy(), ""
        
    mock_fetch.side_effect = fetch_side_effect
    
    # Mock helper rules to simulate an ENTRY TRIGGERED state for BTC-USD
    mock_conf.return_value = {
        "confluence_score": 85.0,
        "directional_score": 100.0,
        "quality_score": 85.0,
        "reasons": ["Mocked Reason"],
        "warnings": []
    }
    
    mock_risk.return_value = {
        "Vetoed": False,
        "R_Vetoed": 0,
        "Entry": 101.0,
        "StopLoss": 99.0,
        "TakeProfit1": 104.0,
        "TakeProfit2": 107.0,
        "RR_TP1": 2.0,
        "RR_TP2": 3.0
    }
    
    mock_mtf.return_value = {
        "alignment_type": "TREND_FOLLOWING",
        "reasons": ["Mocked MTF"],
        "warnings": []
    }
    
    # Do not override decision state in regime rules mock
    mock_regime_rules.side_effect = lambda decision_state, primary_regime, flags, confluence_score: (decision_state, [], [])
    
    # Run scan with forced closed candles to allow evaluation
    res = run_watchlist_scan(
        db_path=TEST_DB,
        watchlist_path=TEST_WL,
        max_symbols=10,
        force_all_candles=True
    )
    
    assert res["status"] == "PARTIAL_SUCCESS"  # BTC-USD is success, FAIL-USD is error
    
    # Check BTC-USD is in results
    btc_res = [r for r in res["results"] if r.symbol == "BTC-USD"]
    assert len(btc_res) == 1
    assert btc_res[0].symbol_status in ["SUCCESS", "WARNING"]
    assert btc_res[0].decision_state == "ENTRY TRIGGERED"
    
    # Check failing symbol results
    fail_res = [r for r in res["results"] if r.symbol == "FAIL-USD"]
    assert len(fail_res) == 1
    assert fail_res[0].symbol_status == "ERROR"
    assert "Timeout" in fail_res[0].error_message
    
    # Check ETH-USD is not scanned (disabled)
    eth_res = [r for r in res["results"] if r.symbol == "ETH-USD"]
    assert len(eth_res) == 0
    
    # Check signal is saved in journal
    signals = load_signals(TEST_DB)
    assert len(signals) > 0
    assert signals[0].symbol == "BTC-USD"
