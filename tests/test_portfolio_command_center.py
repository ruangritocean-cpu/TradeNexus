import pytest
import os
import datetime
from tradenexus.journal.db import init_db
from tradenexus.portfolio.risk_models import PortfolioSettings, SymbolRiskProfile
from tradenexus.portfolio.portfolio_repository import save_portfolio_settings, save_symbol_profile
from tradenexus.scanner.scan_engine import run_watchlist_scan
from tradenexus.scanner.scan_models import ScanRun, ScanResult
from tradenexus.ui.watchlist_helpers import sort_top_actionable_setups

TEST_DB = "data/test_port_cc.sqlite"
TEST_WL = "data/test_port_cc_watchlist.json"

@pytest.fixture(autouse=True)
def setup_cc():
    for f in [TEST_DB, TEST_WL]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except PermissionError:
                pass
    init_db(TEST_DB)
    
    # Create test watchlist with 2 symbols
    import json
    wl_data = [
        {"symbol": "BTC-USD", "display_name": "Bitcoin", "enabled": True, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True},
        {"symbol": "ETH-USD", "display_name": "Ethereum", "enabled": True, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True}
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

def test_portfolio_risk_blocking_preserves_technical_state():
    """
    Verifies that when portfolio risk limits are breached, candidate setups
    are flagged as BLOCKED in alert status and event log, but the raw
    technical_decision_state (ENTRY TRIGGERED) is preserved.
    """
    # 1. Set max open risk to 0% to force BLOCKED status
    settings = PortfolioSettings(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        max_total_open_risk_pct=0.0  # 0% open risk allowed forces BLOCKED
    )
    save_portfolio_settings(settings, TEST_DB)
    
    # 2. Mock yfinance download and indicators to return bullish setups
    import pandas as pd
    from unittest.mock import patch
    
    dates = pd.date_range("2026-01-01 00:00:00", periods=110, freq="h")
    df_mock = pd.DataFrame({
        "Open": [100.0] * 110,
        "High": [102.0] * 110,
        "Low": [98.0] * 110,
        "Close": [101.0] * 110,
        "Volume": [1000.0] * 110
    }, index=dates)
    
    # Mock data fetch
    def fetch_side(ticker, interval, period=None):
        return df_mock.copy(), ""
        
    # Patch scan indicator helpers
    with patch("tradenexus.scanner.scan_engine.fetch_ohlcv_data", side_effect=fetch_side), \
         patch("tradenexus.scanner.scan_engine.calculate_confluence_score") as mock_conf, \
         patch("tradenexus.scanner.scan_engine.validate_trade_risk") as mock_risk, \
         patch("tradenexus.scanner.scan_engine.evaluate_mtf_hierarchy") as mock_mtf, \
         patch("tradenexus.scanner.scan_engine.apply_regime_decision_rules") as mock_rules:
         
        mock_conf.return_value = {
            "confluence_score": 85.0,
            "directional_score": 100.0,
            "quality_score": 85.0,
            "reasons": ["Bullish"],
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
            "reasons": [],
            "warnings": []
        }
        
        mock_rules.side_effect = lambda decision_state, primary_regime, flags, confluence_score: (decision_state, [], [])
        
        res = run_watchlist_scan(
            db_path=TEST_DB,
            watchlist_path=TEST_WL,
            max_symbols=10,
            force_all_candles=True
        )
        
        # Verify results
        btc_res = [r for r in res["results"] if r.symbol == "BTC-USD"][0]
        
        # Technical decision state MUST remain preserved as "ENTRY TRIGGERED"
        assert btc_res.decision_state == "ENTRY TRIGGERED"
        
        # Alert status is blocked by portfolio risk
        assert btc_res.alert_status == "BLOCKED_BY_PORTFOLIO_RISK"
        assert "Total open risk" in btc_res.error_message
        
        # Verify risk event is written to DB
        from tradenexus.portfolio.portfolio_repository import load_risk_events
        events = load_risk_events(db_path=TEST_DB)
        assert len(events) > 0
        symbols = [e.symbol for e in events]
        assert "BTC-USD" in symbols
        assert "ETH-USD" in symbols
        assert events[0].risk_status == "BLOCKED"
