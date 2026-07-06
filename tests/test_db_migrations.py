import pytest
import os
import sqlite3
from tradenexus.journal.db import init_db, get_db_connection

TEST_MIG_DB_PATH = os.path.join("data", "test_db_migration.sqlite")

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(TEST_MIG_DB_PATH):
        try:
            os.remove(TEST_MIG_DB_PATH)
        except PermissionError:
            pass
    yield
    if os.path.exists(TEST_MIG_DB_PATH):
        try:
            os.remove(TEST_MIG_DB_PATH)
        except PermissionError:
            pass

def test_db_migration_workflow():
    """
    Verifies that a database starts at schema_version 1, migrates to v2,
    and is idempotent when run multiple times.
    """
    # 1. Create a legacy v1 database (with signals table but no db_metadata)
    conn = sqlite3.connect(TEST_MIG_DB_PATH)
    with conn:
        conn.execute("""
            CREATE TABLE signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT,
                timeframe TEXT,
                candle_close_time TEXT,
                decision_state TEXT,
                direction TEXT,
                alignment_type TEXT,
                entry REAL,
                sl REAL,
                tp1 REAL,
                tp2 REAL,
                rr_tp1 REAL,
                rr_tp2 REAL,
                confluence_score REAL,
                directional_score REAL,
                quality_score REAL,
                market_bias TEXT,
                setup_direction TEXT,
                trigger_direction TEXT,
                execution_direction TEXT,
                smc_support_source TEXT,
                smc_resistance_source TEXT,
                data_quality_valid INTEGER,
                is_actionable INTEGER,
                outcome_status TEXT,
                outcome_time TEXT,
                bars_to_outcome INTEGER,
                realized_r_multiple REAL,
                reasons_json TEXT,
                warnings_json TEXT,
                created_at TEXT
            );
        """)
    conn.close()
    
    # 2. Run init_db which should detect no metadata -> treat as v1 -> migrate to v4
    init_db(TEST_MIG_DB_PATH)
    
    # Verify migration occurred: check version and columns
    conn = get_db_connection(TEST_MIG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM db_metadata WHERE key='schema_version';")
    version = cursor.fetchone()["value"]
    assert version == "4"
    
    # Check that new column primary_regime exists
    cursor.execute("PRAGMA table_info(signals);")
    cols = [col["name"] for col in cursor.fetchall()]
    assert "primary_regime" in cols
    assert "regime_flags" in cols
    
    # Check scanner tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scan_runs';")
    assert cursor.fetchone() is not None
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scan_results';")
    assert cursor.fetchone() is not None
    
    # Check portfolio tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_settings';")
    assert cursor.fetchone() is not None
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_risk_events';")
    assert cursor.fetchone() is not None
    
    conn.close()
    
    # 3. Running init_db again should be idempotent and not fail
    init_db(TEST_MIG_DB_PATH)
    
    conn = get_db_connection(TEST_MIG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM db_metadata WHERE key='schema_version';")
    version_after = cursor.fetchone()["value"]
    assert version_after == "4"
    conn.close()
