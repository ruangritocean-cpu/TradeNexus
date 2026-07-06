import logging
import sqlite3
from typing import Dict, Any, List
from tradenexus.journal.db import get_db_connection

logger = logging.getLogger(__name__)

def check_database_integrity(db_path: str = None) -> Dict[str, Any]:
    """
    Scans internal tables and constraint structures to diagnose data state.
    """
    errors = []
    warnings = []
    
    required_tables = [
        "db_metadata", "signals", "trades", "alert_log",
        "backtest_runs", "backtest_results", "scan_runs", "scan_results",
        "portfolio_settings", "portfolio_symbol_profiles",
        "portfolio_snapshots", "portfolio_risk_events"
    ]
    
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        # 1. Check Tables Existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [r["name"] for r in cursor.fetchall()]
        
        for table in required_tables:
            if table not in existing_tables:
                errors.append(f"Required table '{table}' is missing from the database schema.")
                
        # 2. Check Signals Table Columns
        if "signals" in existing_tables:
            cursor.execute("PRAGMA table_info(signals);")
            cols = [r["name"] for r in cursor.fetchall()]
            required_cols = ["primary_regime", "regime_flags", "regime_score", "vwap_alignment"]
            for col in required_cols:
                if col not in cols:
                    errors.append(f"Required column '{col}' is missing from 'signals' table.")
                    
        # 3. Check Uniqueness & Duplicate Constraints
        if "signals" in existing_tables:
            cursor.execute("SELECT signal_id, COUNT(*) as c FROM signals GROUP BY signal_id HAVING c > 1;")
            dup_signals = cursor.fetchall()
            if dup_signals:
                errors.append(f"Duplicate signal_id records detected in 'signals' table: {[d['signal_id'] for d in dup_signals]}.")
                
        if "alert_log" in existing_tables:
            cursor.execute("SELECT signal_id, provider, COUNT(*) as c FROM alert_log GROUP BY signal_id, provider HAVING c > 1;")
            dup_alerts = cursor.fetchall()
            if dup_alerts:
                errors.append(f"Duplicate alert_log records detected for: {[(d['signal_id'], d['provider']) for d in dup_alerts]}.")
                
    except Exception as e:
        errors.append(f"Integrity check process failed: {str(e)}")
    finally:
        conn.close()
        
    status = "FAILED" if errors else ("WARNING" if warnings else "OK")
    return {
        "integrity_status": status,
        "errors": errors,
        "warnings": warnings
    }
