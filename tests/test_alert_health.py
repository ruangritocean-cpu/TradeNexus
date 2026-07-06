import pytest
import os
from tradenexus.journal.db import init_db, get_db_connection
from tradenexus.diagnostics.alert_health import check_alert_configuration, simulate_dry_run_alert

TEST_DB = "data/test_diagnostics_alerts.sqlite"

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

def test_alert_config_checks():
    # 1. Config checks flag missing
    cfg = check_alert_configuration(None, None, None)
    assert cfg["discord"] == "NOT_CONFIGURED"
    assert cfg["telegram"] == "NOT_CONFIGURED"
    
    # 2. Config check checks valid patterns
    cfg2 = check_alert_configuration("https://discord.com/api/webhooks/123", "bot_token", "chat_id")
    assert cfg2["discord"] == "CONFIGURED"
    assert cfg2["telegram"] == "CONFIGURED"

def test_dry_run_alert_no_db_write():
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
    
    msg = simulate_dry_run_alert("BTC-USD", "1h", strategy)
    assert "BTC-USD" in msg
    assert "ENTRY TRIGGERED" in msg
    
    # Verify no records written to alert_log
    conn = get_db_connection(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM alert_log;")
    c = cursor.fetchone()[0]
    assert c == 0
    conn.close()
