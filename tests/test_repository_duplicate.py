import os
import pytest
import datetime
from tradenexus.journal.db import init_db
from tradenexus.journal.repository import insert_signal, insert_alert_log
from tradenexus.journal.models import Signal

TEST_DB = "data/test_duplicate_checks.sqlite"

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

def test_insert_duplicate_checks():
    """
    Verifies that insert_signal and insert_alert_log return False when a duplicate row is ignored.
    """
    sig = Signal(
        signal_id="sig_dup_123",
        symbol="BTC-USD",
        timeframe="1h",
        candle_close_time="2026-07-09T12:00:00",
        decision_state="ENTRY TRIGGERED",
        direction="BUY",
        alignment_type="TREND_FOLLOWING",
        entry=50000.0,
        sl=49000.0,
        tp1=52000.0,
        tp2=55000.0,
        rr_tp1=2.0,
        rr_tp2=5.0,
        confluence_score=85.0,
        directional_score=90.0,
        quality_score=80.0,
        market_bias="Bullish",
        setup_direction="Bullish",
        trigger_direction="Bullish",
        execution_direction="Bullish",
        smc_support_source="CONFIRMED_SWING",
        smc_resistance_source="FALLBACK",
        data_quality_valid=1,
        is_actionable=1,
        reasons=["Reason 1"],
        warnings=["Warning 1"]
    )
    
    # First insert -> True
    res1 = insert_signal(sig, TEST_DB)
    assert res1 is True
    
    # Duplicate insert -> False
    res2 = insert_signal(sig, TEST_DB)
    assert res2 is False
    
    # First alert log -> True
    res_alert1 = insert_alert_log("sig_dup_123", "telegram", "SENT", db_path=TEST_DB)
    assert res_alert1 is True
    
    # Duplicate alert log -> False (unique constraint on signal_id + provider)
    res_alert2 = insert_alert_log("sig_dup_123", "telegram", "FAILED", db_path=TEST_DB)
    assert res_alert2 is False
