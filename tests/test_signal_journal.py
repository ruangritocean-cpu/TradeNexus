import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.journal.models import Signal
from tradenexus.journal.repository import generate_signal_id, insert_signal, load_signals

TEST_DB_PATH = os.path.join("data", "test_tradenexus_journal.sqlite")

@pytest.fixture(autouse=True)
def clean_db():
    # Delete test db file if exists
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

def test_deterministic_signal_id():
    """
    Verifies that signal_id generation is deterministic.
    """
    id1 = generate_signal_id("BTC-USD", "15m", "2026-07-06T12:00:00", "ENTRY TRIGGERED", "BUY", 50000.0, 49000.0, 52000.0)
    id2 = generate_signal_id("BTC-USD", "15m", "2026-07-06T12:00:00", "ENTRY TRIGGERED", "BUY", 50000.0, 49000.0, 52000.0)
    id3 = generate_signal_id("BTC-USD", "15m", "2026-07-06T12:00:00", "ENTRY TRIGGERED", "BUY", 50000.000001, 49000.0, 52000.0) # Rounded
    
    assert id1 == id2
    assert id1 == id3

def test_insert_and_duplicate_prevention():
    """
    Verifies signals can be inserted and duplicate signal_ids are safely ignored.
    """
    sig = Signal(
        signal_id="test_id_123",
        symbol="BTC-USD",
        timeframe="15m",
        candle_close_time="2026-07-06T12:00:00",
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
    
    # First insert
    res1 = insert_signal(sig, TEST_DB_PATH)
    assert res1
    
    # Load and verify
    signals = load_signals(TEST_DB_PATH)
    assert len(signals) == 1
    assert signals[0].signal_id == "test_id_123"
    
    # Second insert of the same signal (should ignore and return False)
    res2 = insert_signal(sig, TEST_DB_PATH)
    assert not res2
    
    # Check count is still 1
    signals = load_signals(TEST_DB_PATH)
    assert len(signals) == 1
