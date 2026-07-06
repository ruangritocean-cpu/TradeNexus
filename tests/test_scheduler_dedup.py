import pytest
import time
import os
from unittest.mock import patch, MagicMock
from tradenexus.scanner.scheduler import (
    trigger_scheduled_scan,
    get_scheduler_status,
    reset_scheduler_state
)
from tradenexus.journal.db import init_db
from tradenexus.alerts.dispatcher import dispatch_alert

TEST_DB = "data/test_sched_dedup.sqlite"

@pytest.fixture(autouse=True)
def setup_te():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    init_db(TEST_DB)
    reset_scheduler_state()
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass

@patch("tradenexus.scanner.scheduler.run_watchlist_scan")
def test_scheduler_overlap_and_rate_limit(mock_scan):
    """
    Verifies scheduler status transition, overlap scan skips, and rate-limit guard.
    """
    # 1. Mock run_watchlist_scan to simulate success
    mock_scan.return_value = {"scan_run_id": "mock_run_111"}
    
    # Trigger first scan
    res1 = trigger_scheduled_scan(
        db_path=TEST_DB,
        max_symbols=5,
        min_seconds_between_scans=5
    )
    
    assert res1["status"] == "COMPLETED"
    assert get_scheduler_status()["scheduler_state"] == "COMPLETED"
    
    # 2. Trigger second scan immediately -> should fail rate-limit
    res2 = trigger_scheduled_scan(
        db_path=TEST_DB,
        max_symbols=5,
        min_seconds_between_scans=5
    )
    assert res2["status"] == "FAILED"
    assert "rate-limited" in res2["error_message"]

@patch("tradenexus.alerts.dispatcher.send_telegram_message")
def test_alert_deduplication(mock_tg):
    """
    Verifies that the alert dispatcher prevents sending the same signal_id twice.
    """
    mock_tg.return_value = (True, "")
    
    strategy = {
        "Decision": "ENTRY TRIGGERED",
        "Direction": "BUY",
        "AlignmentType": "TREND_FOLLOWING",
        "Entry": 100.0,
        "StopLoss": 95.0,
        "TakeProfit1": 105.0,
        "TakeProfit2": 110.0,
        "RR_TP1": 2.0,
        "ConfluenceScore": 85.0,
        "Regime": "TRENDING_UP",
        "Reasons": [],
        "Warnings": []
    }
    
    # Dispatch first time -> success
    res1 = dispatch_alert(
        signal_id="sig_test_dedup",
        ticker="BTC-USD",
        timeframe="1h",
        strategy=strategy,
        tg_bot_token="bot_123",
        tg_chat_id="chat_123",
        db_path=TEST_DB
    )
    assert res1["telegram"] is True
    
    # Dispatch second time -> should skip telegram send and return True (cached success)
    # mock_tg should not be called again
    mock_tg.reset_mock()
    res2 = dispatch_alert(
        signal_id="sig_test_dedup",
        ticker="BTC-USD",
        timeframe="1h",
        strategy=strategy,
        tg_bot_token="bot_123",
        tg_chat_id="chat_123",
        db_path=TEST_DB
    )
    assert res2["telegram"] is True
    mock_tg.assert_not_called()
