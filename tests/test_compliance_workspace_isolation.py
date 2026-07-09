import pytest
import os
import sqlite3
from tradenexus.journal.db import init_db
from tradenexus.reports.compliance_engine import generate_compliance_report

TEST_DB = "data/test_compliance_isolation.sqlite"

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

def test_workspace_isolation_in_reports():
    """
    Verifies that workspace A report does not include workspace B signals, alerts, or trades.
    """
    conn = sqlite3.connect(TEST_DB)
    try:
        with conn:
            # Workspace A: crypto_desk
            conn.execute("""
                INSERT INTO signals (signal_id, symbol, timeframe, candle_close_time, is_actionable, workspace_id)
                VALUES ('sig_a', 'BTC-USD', '1h', '2026-07-09T10:00:00Z', 1, 'crypto_desk')
            """)
            conn.execute("""
                INSERT INTO alert_log (signal_id, provider, status, sent_at, workspace_id)
                VALUES ('sig_a', 'discord', 'SENT', '2026-07-09T10:05:00Z', 'crypto_desk')
            """)
            conn.execute("""
                INSERT INTO trades (trade_id, signal_id, symbol, direction, status, opened_at, workspace_id)
                VALUES ('t_a', 'sig_a', 'BTC-USD', 'BUY', 'OPEN', '2026-07-09T10:10:00Z', 'crypto_desk')
            """)
            
            # Workspace B: futures_desk
            conn.execute("""
                INSERT INTO signals (signal_id, symbol, timeframe, candle_close_time, is_actionable, workspace_id)
                VALUES ('sig_b', 'GC=F', '4h', '2026-07-09T11:00:00Z', 1, 'futures_desk')
            """)
    finally:
        conn.close()

    # 1. Check Crypto Desk report
    report_a = generate_compliance_report(
        workspace_id="crypto_desk",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    assert report_a.metrics.total_signals == 1
    assert report_a.metrics.alerts_sent == 1
    assert report_a.metrics.trades_opened == 1
    
    # 2. Check Futures Desk report
    report_b = generate_compliance_report(
        workspace_id="futures_desk",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    assert report_b.metrics.total_signals == 1
    assert report_b.metrics.alerts_sent == 0
    assert report_b.metrics.trades_opened == 0
