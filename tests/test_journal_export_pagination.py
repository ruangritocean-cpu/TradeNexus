import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.journal.models import Signal
from tradenexus.journal.repository import (
    insert_signal,
    load_signals_paginated,
    export_signals_to_csv,
    clear_backtest_results,
    load_signals
)

TEST_PAG_DB_PATH = os.path.join("data", "test_journal_pag.sqlite")

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_PAG_DB_PATH):
        try:
            os.remove(TEST_PAG_DB_PATH)
        except PermissionError:
            pass
    init_db(TEST_PAG_DB_PATH)
    yield
    if os.path.exists(TEST_PAG_DB_PATH):
        try:
            os.remove(TEST_PAG_DB_PATH)
        except PermissionError:
            pass

def test_pagination_and_export():
    """
    Verifies that pagination retrieves the correct subset of signals,
    CSV exports run without error, and clearing backtests doesn't delete live signals.
    """
    # Create 5 mock signals
    for i in range(5):
        sig = Signal(
            signal_id=f"sig_{i}",
            symbol="BTC-USD",
            timeframe="15m",
            candle_close_time=f"2026-07-06T12:0{i}:00Z",
            decision_state="ENTRY TRIGGERED",
            direction="BUY",
            alignment_type="TREND_FOLLOWING",
            entry=100.0,
            sl=90.0,
            tp1=115.0,
            tp2=130.0,
            rr_tp1=1.5,
            rr_tp2=3.0,
            confluence_score=85.0,
            directional_score=80.0,
            quality_score=90.0,
            market_bias="Bullish",
            setup_direction="Bullish",
            trigger_direction="Bullish",
            execution_direction="Bullish",
            smc_support_source="CONFIRMED_SWING",
            smc_resistance_source="CONFIRMED_SWING",
            data_quality_valid=1,
            is_actionable=1,
            reasons=[],
            warnings=[]
        )
        insert_signal(sig, TEST_PAG_DB_PATH)
        
    # Test pagination: limit = 2, offset = 1 -> should return 2 rows (offset by 1)
    pag_sigs = load_signals_paginated(limit=2, offset=1, db_path=TEST_PAG_DB_PATH)
    assert len(pag_sigs) == 2
    
    # Test CSV export
    csv_str = export_signals_to_csv(TEST_PAG_DB_PATH)
    assert "signal_id" in csv_str
    assert "BTC-USD" in csv_str
    
    # Test clear_backtest_results does not clear signals
    clear_backtest_results(TEST_PAG_DB_PATH)
    all_sigs = load_signals(TEST_PAG_DB_PATH)
    assert len(all_sigs) == 5
