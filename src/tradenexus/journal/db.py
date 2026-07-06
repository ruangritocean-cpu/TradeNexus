import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join("data", "tradenexus_journal.sqlite")

def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Returns a connection to the SQLite database.
    Creates parent directories if necessary and sets WAL mode.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
        
    dir_name = os.path.dirname(db_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = None):
    """
    Creates tables and performs migrations if necessary.
    """
    conn = get_db_connection(db_path)
    try:
        # Check if we need to migrate
        cursor = conn.cursor()
        
        # Check if db_metadata table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata';")
        has_metadata = cursor.fetchone() is not None
        
        # Check if signals table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals';")
        has_signals = cursor.fetchone() is not None
        
        current_version = 1
        if has_metadata:
            cursor.execute("SELECT value FROM db_metadata WHERE key='schema_version';")
            row = cursor.fetchone()
            if row:
                current_version = int(row["value"])
        elif not has_signals:
            # New database, set version directly to 4
            current_version = 4
            
        # Write tables
        with conn:
            # 1. db_metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS db_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            
            # 2. Signals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
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
                    outcome_status TEXT DEFAULT 'OPEN',
                    outcome_time TEXT,
                    bars_to_outcome INTEGER,
                    realized_r_multiple REAL DEFAULT 0.0,
                    reasons_json TEXT,
                    warnings_json TEXT,
                    created_at TEXT
                );
            """)
            
            # 3. alert_log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT,
                    provider TEXT,
                    status TEXT,
                    sent_at TEXT,
                    error_message TEXT,
                    UNIQUE(signal_id, provider)
                );
            """)
            
            # 4. trades
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    signal_id TEXT,
                    symbol TEXT,
                    direction TEXT,
                    entry REAL,
                    sl REAL,
                    tp1 REAL,
                    tp2 REAL,
                    status TEXT,
                    opened_at TEXT,
                    closed_at TEXT,
                    realized_r_multiple REAL
                );
            """)
            
            # 5. backtest_runs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    run_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    timeframe TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    rr_threshold REAL,
                    max_bars_to_hold INTEGER,
                    created_at TEXT,
                    config_json TEXT
                );
            """)
            
            # 6. backtest_results
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    signal_id TEXT,
                    outcome_status TEXT,
                    realized_r_multiple REAL,
                    bars_to_outcome INTEGER
                );
            """)
            
            # 7. scan_runs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    scan_run_id TEXT PRIMARY KEY,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT,
                    total_symbols INTEGER,
                    success_count INTEGER,
                    warning_count INTEGER,
                    error_count INTEGER,
                    skipped_count INTEGER,
                    config_json TEXT
                );
            """)
            
            # 8. scan_results
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id TEXT,
                    signal_id TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    scan_time TEXT,
                    symbol_status TEXT,
                    decision_state TEXT,
                    direction TEXT,
                    alignment_type TEXT,
                    confluence_score REAL,
                    rr_tp1 REAL,
                    primary_regime TEXT,
                    regime_flags_json TEXT,
                    data_quality_status TEXT,
                    alert_status TEXT,
                    journal_status TEXT,
                    reasons_json TEXT,
                    warnings_json TEXT,
                    error_message TEXT,
                    created_at TEXT
                );
            """)
            
            # 9. portfolio_settings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_settings (
                    id INTEGER PRIMARY KEY,
                    account_equity REAL,
                    risk_per_trade_pct REAL,
                    max_daily_risk_pct REAL,
                    max_total_open_risk_pct REAL,
                    max_concurrent_trades INTEGER,
                    max_same_direction_trades INTEGER,
                    max_correlated_positions INTEGER,
                    correlation_threshold REAL,
                    correlation_lookback_bars INTEGER,
                    correlation_cache_ttl_seconds INTEGER,
                    default_contract_multiplier REAL,
                    default_point_value REAL,
                    currency TEXT,
                    updated_at TEXT
                );
            """)
            
            # 10. portfolio_symbol_profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_symbol_profiles (
                    symbol TEXT PRIMARY KEY,
                    asset_class TEXT,
                    point_value REAL,
                    contract_multiplier REAL,
                    min_position_size REAL,
                    position_step REAL,
                    currency TEXT,
                    updated_at TEXT
                );
            """)
            
            # 11. portfolio_snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    realized_daily_risk REAL,
                    open_risk REAL,
                    open_risk_pct REAL,
                    potential_setup_risk REAL,
                    potential_setup_risk_pct REAL,
                    active_trade_count INTEGER,
                    actionable_setup_count INTEGER,
                    risk_status TEXT,
                    warnings_json TEXT,
                    details_json TEXT
                );
            """)
            
            # 12. portfolio_risk_events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_risk_events (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    signal_id TEXT,
                    trade_id TEXT,
                    symbol TEXT,
                    event_type TEXT,
                    risk_status TEXT,
                    reason TEXT,
                    details_json TEXT
                );
            """)
            
            # Save version to db_metadata
            conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', ?);", (str(current_version),))
            
        # Execute migration from version 1 to 2 if needed
        if current_version == 1:
            logger.info("Migrating database from version 1 to 2...")
            with conn:
                new_cols = [
                    ("primary_regime", "TEXT"),
                    ("regime_flags", "TEXT"),
                    ("regime_score", "REAL"),
                    ("volume_confirmation", "TEXT"),
                    ("vwap_alignment", "TEXT"),
                    ("bos_present", "INTEGER"),
                    ("choch_present", "INTEGER"),
                    ("fvg_present", "INTEGER"),
                    ("liquidity_sweep_present", "INTEGER")
                ]
                cursor.execute("PRAGMA table_info(signals);")
                existing_cols = [col["name"] for col in cursor.fetchall()]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type};")
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '2');")
            current_version = 2
            logger.info("Migration to version 2 completed successfully.")
            
        # Execute migration from version 2 to 3 if needed
        if current_version == 2:
            logger.info("Migrating database from version 2 to 3...")
            with conn:
                cursor.execute("PRAGMA table_info(signals);")
                existing_cols = [col["name"] for col in cursor.fetchall()]
                new_cols = [
                    ("primary_regime", "TEXT"),
                    ("regime_flags", "TEXT"),
                    ("regime_score", "REAL"),
                    ("volume_confirmation", "TEXT"),
                    ("vwap_alignment", "TEXT"),
                    ("bos_present", "INTEGER"),
                    ("choch_present", "INTEGER"),
                    ("fvg_present", "INTEGER"),
                    ("liquidity_sweep_present", "INTEGER")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type};")
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '3');")
            current_version = 3
            logger.info("Migration to version 3 completed successfully.")
            
        # Execute migration from version 3 to 4 if needed
        if current_version == 3:
            logger.info("Migrating database from version 3 to 4...")
            with conn:
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '4');")
            current_version = 4
            logger.info("Migration to version 4 completed successfully.")
            
        elif current_version == 4:
            # Ensure compatibility columns exist on signals table
            with conn:
                cursor.execute("PRAGMA table_info(signals);")
                existing_cols = [col["name"] for col in cursor.fetchall()]
                new_cols = [
                    ("primary_regime", "TEXT"),
                    ("regime_flags", "TEXT"),
                    ("regime_score", "REAL"),
                    ("volume_confirmation", "TEXT"),
                    ("vwap_alignment", "TEXT"),
                    ("bos_present", "INTEGER"),
                    ("choch_present", "INTEGER"),
                    ("fvg_present", "INTEGER"),
                    ("liquidity_sweep_present", "INTEGER")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type};")
            
    except Exception as e:
        logger.error(f"Error during database initialization/migration: {str(e)}")
        raise e
    finally:
        conn.close()
