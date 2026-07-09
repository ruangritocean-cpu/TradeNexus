import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.journal.repository import check_alert_exists, insert_alert_log
from tradenexus.alerts.dispatcher import dispatch_alert

TEST_DB_PATH = os.path.join("data", "test_alert_dedup.sqlite")

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

def test_alert_deduplication():
    """
    Verifies that the alert dispatcher logs alerts and prevents sending duplicate
    alerts for the same signal_id per provider.
    """
    signal_id = "test_alert_sig_999"
    strategy = {
        "Decision": "ENTRY TRIGGERED",
        "Direction": "BUY",
        "AlignmentType": "TREND_FOLLOWING",
        "Entry": 100.0,
        "StopLoss": 90.0,
        "TakeProfit1": 115.0,
        "TakeProfit2": 130.0,
        "RR_TP1": 1.5,
        "ConfluenceScore": 85.0,
        "Reasons": ["Trend matched"],
        "Warnings": []
    }
    
    # Check initial state (doesn't exist)
    assert not check_alert_exists(signal_id, "discord", TEST_DB_PATH)
    assert not check_alert_exists(signal_id, "telegram", TEST_DB_PATH)
    
    # Insert logs manually (mocking successful send)
    insert_alert_log(signal_id, "discord", "SUCCESS", None, TEST_DB_PATH)
    
    # Check status
    assert check_alert_exists(signal_id, "discord", TEST_DB_PATH)
    assert not check_alert_exists(signal_id, "telegram", TEST_DB_PATH) # Telegram should still be allowed
    
    # Try calling dispatcher with configured mock endpoints (using invalid/none urls to bypass sending but verify skip)
    res = dispatch_alert(
        signal_id=signal_id,
        ticker="AAPL",
        timeframe="15m",
        strategy=strategy,
        discord_webhook_url="http://mock-url.com", # Should skip since discord is already marked sent
        tg_bot_token=None,
        tg_chat_id=None,
        db_path=TEST_DB_PATH
    )
    
    # Since discord exists, dispatcher skips and returns SKIPPED_DUPLICATE
    assert res["discord"] == "SKIPPED_DUPLICATE"
    assert res["telegram"] == "NOT_CONFIGURED" # None token skips entirely
