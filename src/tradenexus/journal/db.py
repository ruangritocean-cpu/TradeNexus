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
            # New database, start at 1 and migrate linearly
            current_version = 1
            
        # Write tables
        try:
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
                    provider_used TEXT,
                    fallback_used INTEGER,
                    data_quality_warnings_json TEXT,
                    data_quality_errors_json TEXT,
                    latest_candle_time TEXT,
                    bars_available INTEGER,
                    alert_status TEXT,
                    journal_status TEXT,
                    reasons_json TEXT,
                    warnings_json TEXT,
                    error_message TEXT,
                    created_at TEXT,
                    position_size_units REAL,
                    candidate_risk_amount REAL,
                    candidate_risk_pct REAL
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
            
            # 13. optimization_runs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_runs (
                    run_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    timeframe TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    train_window_bars INTEGER,
                    test_window_bars INTEGER,
                    step_bars INTEGER,
                    max_combinations INTEGER,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    config_json TEXT,
                    sampling_seed INTEGER,
                    sampling_method TEXT,
                    grid_total_combinations INTEGER,
                    grid_evaluated_combinations INTEGER
                );
            """)
            
            # 14. optimization_results
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    window_index INTEGER,
                    train_start TEXT,
                    train_end TEXT,
                    test_start TEXT,
                    test_end TEXT,
                    params_json TEXT,
                    in_sample_metrics_json TEXT,
                    out_sample_metrics_json TEXT,
                    robustness_score REAL,
                    warnings_json TEXT
                );
            """)
            
            # 15. parameter_recommendations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parameter_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    timeframe TEXT,
                    params_json TEXT,
                    robustness_score REAL,
                    sample_size INTEGER,
                    recommendation_status TEXT,
                    valid_from TEXT,
                    created_at TEXT,
                    notes TEXT
                );
            """)

            # 16. playbooks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playbooks (
                    playbook_id TEXT PRIMARY KEY,
                    name TEXT,
                    enabled INTEGER,
                    allowed_symbols TEXT,
                    allowed_asset_classes TEXT,
                    allowed_timeframes TEXT,
                    allowed_setup_types TEXT,
                    min_confluence_score REAL,
                    min_rr REAL,
                    allowed_regimes TEXT,
                    blocked_regimes TEXT,
                    max_trades_per_day INTEGER,
                    max_losses_per_day INTEGER,
                    max_consecutive_losses INTEGER,
                    allowed_sessions TEXT,
                    cooldown_minutes_after_loss INTEGER,
                    created_at TEXT,
                    notes TEXT
                );
            """)

            # 17. playbook_rule_events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playbook_rule_events (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    playbook_id TEXT,
                    symbol TEXT,
                    rule_name TEXT,
                    event_type TEXT,
                    decision_state TEXT,
                    details_json TEXT
                );
            """)

            # 18. daily_trading_state
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_trading_state (
                    date TEXT PRIMARY KEY,
                    trades_count INTEGER,
                    losses_count INTEGER,
                    consecutive_losses INTEGER,
                    last_loss_time TEXT,
                    updated_at TEXT
                );
            """)
            
            # Indexes for Query Speed Optimization
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(candle_close_time DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_tf ON signals(symbol, timeframe);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_actionable ON signals(is_actionable, candle_close_time DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_log_signal_provider ON alert_log(signal_id, provider);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_results_run ON scan_results(scan_run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_results_symbol ON scan_results(symbol, timeframe);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_events_time ON portfolio_risk_events(created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opt_results_run ON optimization_results(run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opt_recommendations_symbol ON parameter_recommendations(symbol, timeframe);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_playbook_rule_events_time ON playbook_rule_events(created_at DESC);")
            
            # Self-healing schema upgrade for older databases
            try:
                cursor.execute("PRAGMA table_info(scan_results);")
                columns = [col["name"] for col in cursor.fetchall()]
                if "position_size_units" not in columns:
                    conn.execute("ALTER TABLE scan_results ADD COLUMN position_size_units REAL;")
                if "candidate_risk_amount" not in columns:
                    conn.execute("ALTER TABLE scan_results ADD COLUMN candidate_risk_amount REAL;")
                if "candidate_risk_pct" not in columns:
                    conn.execute("ALTER TABLE scan_results ADD COLUMN candidate_risk_pct REAL;")
            except Exception as alter_err:
                logger.warning(f"Could not perform self-healing ALTER TABLE for scan_results: {alter_err}")

            # Save version to db_metadata
            conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', ?);", (str(current_version),))
            conn.commit()
            
            # Post-creation schema validation
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [r["name"] for r in cursor.fetchall()]
            logger.info(f"Initialized database tables successfully: {existing_tables}")
            
            # Verification check
            if "portfolio_settings" not in existing_tables:
                logger.critical("CRITICAL: portfolio_settings table was NOT created after explicit commit!")
                
        except Exception as table_err:
            logger.error(f"Error creating database tables: {str(table_err)}")
            conn.rollback()
            raise table_err
            
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
            
        # Execute migration from version 4 to 5 if needed
        if current_version == 4:
            logger.info("Migrating database from version 4 to 5...")
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
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS optimization_runs (
                        run_id TEXT PRIMARY KEY,
                        symbol TEXT,
                        timeframe TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        train_window_bars INTEGER,
                        test_window_bars INTEGER,
                        step_bars INTEGER,
                        max_combinations INTEGER,
                        status TEXT,
                        created_at TEXT,
                        completed_at TEXT,
                        config_json TEXT,
                        sampling_seed INTEGER,
                        sampling_method TEXT,
                        grid_total_combinations INTEGER,
                        grid_evaluated_combinations INTEGER
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS optimization_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        window_index INTEGER,
                        train_start TEXT,
                        train_end TEXT,
                        test_start TEXT,
                        test_end TEXT,
                        params_json TEXT,
                        in_sample_metrics_json TEXT,
                        out_sample_metrics_json TEXT,
                        robustness_score REAL,
                        warnings_json TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS parameter_recommendations (
                        recommendation_id TEXT PRIMARY KEY,
                        symbol TEXT,
                        timeframe TEXT,
                        params_json TEXT,
                        robustness_score REAL,
                        sample_size INTEGER,
                        recommendation_status TEXT,
                        valid_from TEXT,
                        created_at TEXT,
                        notes TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_opt_results_run ON optimization_results(run_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_opt_recommendations_symbol ON parameter_recommendations(symbol, timeframe);")
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '5');")
            current_version = 5
            logger.info("Migration to version 5 completed successfully.")

        # Execute migration from version 5 to 6 if needed
        if current_version == 5:
            logger.info("Migrating database from version 5 to 6...")
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS playbooks (
                        playbook_id TEXT PRIMARY KEY,
                        name TEXT,
                        enabled INTEGER,
                        allowed_symbols TEXT,
                        allowed_asset_classes TEXT,
                        allowed_timeframes TEXT,
                        allowed_setup_types TEXT,
                        min_confluence_score REAL,
                        min_rr REAL,
                        allowed_regimes TEXT,
                        blocked_regimes TEXT,
                        max_trades_per_day INTEGER,
                        max_losses_per_day INTEGER,
                        max_consecutive_losses INTEGER,
                        allowed_sessions TEXT,
                        cooldown_minutes_after_loss INTEGER,
                        created_at TEXT,
                        notes TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS playbook_rule_events (
                        event_id TEXT PRIMARY KEY,
                        created_at TEXT,
                        playbook_id TEXT,
                        symbol TEXT,
                        rule_name TEXT,
                        event_type TEXT,
                        decision_state TEXT,
                        details_json TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS daily_trading_state (
                        date TEXT PRIMARY KEY,
                        trades_count INTEGER,
                        losses_count INTEGER,
                        consecutive_losses INTEGER,
                        last_loss_time TEXT,
                        updated_at TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_playbook_rule_events_time ON playbook_rule_events(created_at DESC);")
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '6');")
            current_version = 6
            logger.info("Migration to version 6 completed successfully.")
            
        # Execute migration from version 6 to 7 if needed
        if current_version == 6:
            logger.info("Migrating database from version 6 to 7...")
            with conn:
                cursor.execute("PRAGMA table_info(scan_results);")
                existing_cols = [col["name"] for col in cursor.fetchall()]
                new_cols = [
                    ("provider_used", "TEXT"),
                    ("fallback_used", "INTEGER"),
                    ("data_quality_warnings_json", "TEXT"),
                    ("data_quality_errors_json", "TEXT"),
                    ("latest_candle_time", "TEXT"),
                    ("bars_available", "INTEGER")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE scan_results ADD COLUMN {col_name} {col_type};")
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '7');")
            current_version = 7
            logger.info("Migration to version 7 completed successfully.")
            
        # Execute migration from version 7 to 8 if needed
        if current_version == 7:
            logger.info("Migrating database from version 7 to 8...")
            with conn:
                # 1. Create workspaces table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS workspaces (
                        workspace_id TEXT PRIMARY KEY,
                        workspace_name TEXT,
                        owner_label TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        is_active INTEGER,
                        notes TEXT
                    );
                """)
                # Insert default workspace
                import datetime
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute("""
                    INSERT OR IGNORE INTO workspaces (workspace_id, workspace_name, owner_label, created_at, updated_at, is_active, notes)
                    VALUES ('default_workspace', 'Default Workspace', 'System', ?, ?, 1, 'Default System Workspace');
                """, (now_str, now_str))
                
                # Helper to migrate tables with new primary keys or constraints
                def migrate_table_schema(table_name, pk_or_unique_sql):
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    cols_info = cursor.fetchall()
                    col_defs = []
                    col_names = []
                    for col in cols_info:
                        name = col["name"]
                        ctype = col["type"]
                        if name == "workspace_id":
                            continue
                        col_names.append(name)
                        col_defs.append(f"{name} {ctype}")
                    col_defs.append("workspace_id TEXT DEFAULT 'default_workspace'")
                    
                    conn.execute(f"ALTER TABLE {table_name} RENAME TO old_{table_name};")
                    create_sql = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs)
                    if pk_or_unique_sql:
                        create_sql += f",\n{pk_or_unique_sql}"
                    create_sql += "\n);"
                    conn.execute(create_sql)
                    
                    cols_joined = ", ".join(col_names)
                    conn.execute(f"INSERT INTO {table_name} ({cols_joined}, workspace_id) SELECT {cols_joined}, 'default_workspace' FROM old_{table_name};")
                    conn.execute(f"DROP TABLE old_{table_name};")

                # Migrate composite PK/Unique constraint tables
                migrate_table_schema("signals", "PRIMARY KEY(signal_id, workspace_id)")
                migrate_table_schema("alert_log", "UNIQUE(signal_id, provider, workspace_id)")
                migrate_table_schema("playbooks", "PRIMARY KEY(playbook_id, workspace_id)")
                migrate_table_schema("daily_trading_state", "PRIMARY KEY(date, workspace_id)")
                migrate_table_schema("portfolio_settings", "PRIMARY KEY(id, workspace_id)")
                migrate_table_schema("portfolio_symbol_profiles", "PRIMARY KEY(symbol, workspace_id)")
                
                # Add workspace_id to remaining tables
                other_tables = [
                    "trades",
                    "scan_runs",
                    "scan_results",
                    "portfolio_snapshots",
                    "portfolio_risk_events",
                    "optimization_runs",
                    "optimization_results",
                    "parameter_recommendations",
                    "playbook_rule_events"
                ]
                for t in other_tables:
                    cursor.execute(f"PRAGMA table_info({t});")
                    cols = [col["name"] for col in cursor.fetchall()]
                    if "workspace_id" not in cols:
                        conn.execute(f"ALTER TABLE {t} ADD COLUMN workspace_id TEXT DEFAULT 'default_workspace';")
                        
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '8');")
            current_version = 8
            logger.info("Migration to version 8 completed successfully.")
            
        # Execute migration from version 8 to 9 if needed
        if current_version == 8:
            logger.info("Migrating database from version 8 to 9...")
            with conn:
                # 1. Add active_preset_id TEXT to playbooks table idempotently
                cursor.execute("PRAGMA table_info(playbooks);")
                cols = [col["name"] for col in cursor.fetchall()]
                if "active_preset_id" not in cols:
                    conn.execute("ALTER TABLE playbooks ADD COLUMN active_preset_id TEXT;")
                    
                # 2. Create strategy_presets table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_presets (
                        preset_id TEXT,
                        workspace_id TEXT,
                        name TEXT,
                        description TEXT,
                        asset_class TEXT,
                        trading_style TEXT,
                        risk_profile TEXT,
                        allowed_symbols_json TEXT,
                        allowed_timeframes_json TEXT,
                        allowed_sessions_json TEXT,
                        allowed_setup_types_json TEXT,
                        allowed_regimes_json TEXT,
                        blocked_regimes_json TEXT,
                        min_confluence_score REAL,
                        min_rr REAL,
                        max_trades_per_day INTEGER,
                        max_losses_per_day INTEGER,
                        max_consecutive_losses INTEGER,
                        cooldown_minutes_after_loss INTEGER,
                        default_portfolio_risk_pct REAL,
                        suggested_symbols_json TEXT,
                        notes TEXT,
                        tags_json TEXT,
                        is_builtin INTEGER,
                        created_at TEXT,
                        updated_at TEXT,
                        PRIMARY KEY(preset_id, workspace_id)
                    );
                """)
                
                # 3. Create preset_apply_history table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS preset_apply_history (
                        apply_id TEXT PRIMARY KEY,
                        preset_id TEXT,
                        workspace_id TEXT,
                        applied_at TEXT,
                        applied_sections_json TEXT,
                        previous_values_json TEXT,
                        new_values_json TEXT,
                        warnings_json TEXT,
                        applied_by_label TEXT
                    );
                """)
                
                # 4. Seed built-in presets
                seed_builtin_presets(conn)
                
                conn.execute("INSERT OR REPLACE INTO db_metadata (key, value) VALUES ('schema_version', '9');")
            current_version = 9
            logger.info("Migration to version 9 completed successfully.")
            
    except Exception as e:
        logger.error(f"Error during database initialization/migration: {str(e)}")
        raise e
    finally:
        conn.close()

def seed_builtin_presets(conn: sqlite3.Connection):
    from tradenexus.presets.preset_library import get_builtin_presets
    import json
    
    presets = get_builtin_presets()
    for p in presets:
        conn.execute("""
            INSERT OR REPLACE INTO strategy_presets (
                preset_id, workspace_id, name, description, asset_class, trading_style, risk_profile,
                allowed_symbols_json, allowed_timeframes_json, allowed_sessions_json, allowed_setup_types_json,
                allowed_regimes_json, blocked_regimes_json, min_confluence_score, min_rr, max_trades_per_day,
                max_losses_per_day, max_consecutive_losses, cooldown_minutes_after_loss, default_portfolio_risk_pct,
                suggested_symbols_json, notes, tags_json, is_builtin, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            p.preset_id,
            p.workspace_id,
            p.name,
            p.description,
            p.asset_class,
            p.trading_style,
            p.risk_profile,
            json.dumps(p.allowed_symbols),
            json.dumps(p.allowed_timeframes),
            json.dumps(p.allowed_sessions),
            json.dumps(p.allowed_setup_types),
            json.dumps(p.allowed_regimes),
            json.dumps(p.blocked_regimes),
            p.min_confluence_score,
            p.min_rr,
            p.max_trades_per_day,
            p.max_losses_per_day,
            p.max_consecutive_losses,
            p.cooldown_minutes_after_loss,
            p.default_portfolio_risk_pct,
            json.dumps(p.suggested_symbols),
            p.notes,
            json.dumps(p.tags),
            p.is_builtin,
            p.created_at,
            p.updated_at
        ))
