import pytest
import os
import sqlite3
from tradenexus.journal.db import init_db
from tradenexus.reports.compliance_engine import generate_compliance_report

TEST_DB = "data/test_compliance_engine.sqlite"

@pytest.fixture(autouse=True)
def setup_teardown():
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

def test_empty_compliance_report_safety():
    """
    Verifies that running compliance report on an empty database does not crash.
    """
    report = generate_compliance_report(
        workspace_id="default_workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    assert report.workspace_id == "default_workspace"
    assert report.compliance_score == 100.0
    assert report.metrics.total_signals == 0
    assert report.metrics.win_rate == 0.0

def test_utc_date_filtering():
    """
    Verifies that date bounds filter records strictly in UTC.
    """
    conn = sqlite3.connect(TEST_DB)
    # Insert signals at different timestamps
    try:
        with conn:
            conn.execute("""
                INSERT INTO signals (signal_id, symbol, timeframe, candle_close_time, is_actionable, workspace_id)
                VALUES ('sig1', 'BTC-USD', '1h', '2026-07-09T05:00:00Z', 1, 'default_workspace')
            """)
            conn.execute("""
                INSERT INTO signals (signal_id, symbol, timeframe, candle_close_time, is_actionable, workspace_id)
                VALUES ('sig2', 'BTC-USD', '1h', '2026-07-09T18:00:00Z', 1, 'default_workspace')
            """)
            conn.execute("""
                INSERT INTO signals (signal_id, symbol, timeframe, candle_close_time, is_actionable, workspace_id)
                VALUES ('sig3', 'BTC-USD', '1h', '2026-07-10T02:00:00Z', 1, 'default_workspace')
            """)
    finally:
        conn.close()

    # Query only for July 9th
    report = generate_compliance_report(
        workspace_id="default_workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    assert report.metrics.total_signals == 2  # sig1 and sig2 only
    
    # Query July 10th
    report_next = generate_compliance_report(
        workspace_id="default_workspace",
        start_date="2026-07-10T00:00:00Z",
        end_date="2026-07-10T23:59:59Z",
        db_path=TEST_DB
    )
    assert report_next.metrics.total_signals == 1  # sig3 only
