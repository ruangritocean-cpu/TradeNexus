import os
import datetime
import logging
import sqlite3
from typing import Dict, Any, List
from tradenexus.journal.db import get_db_connection

logger = logging.getLogger(__name__)

def check_system_health(
    db_path: str = None,
    watchlist_path: str = None,
    discord_webhook: str = None,
    tg_bot_token: str = None
) -> Dict[str, Any]:
    """
    Evaluates health checks across database, environment settings, and provider connections.
    Returns:
        Dict: Health status summary.
    """
    errors = []
    warnings = []
    checks = {}
    
    # 1. DB Connectivity & Version Check
    db_ok = False
    db_ver = "Unknown"
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM db_metadata WHERE key='schema_version';")
        row = cursor.fetchone()
        if row:
            db_ver = row["value"]
            db_ok = True
            checks["database_connection"] = "OK"
            checks["schema_version"] = db_ver
        else:
            warnings.append("Database metadata table exists but schema_version is missing.")
            checks["database_connection"] = "WARNING"
        conn.close()
    except Exception as e:
        errors.append(f"Database connection failed: {str(e)}")
        checks["database_connection"] = "FAILED"
        
    # 2. Journal Write/Read Check
    if db_ok:
        try:
            conn = get_db_connection(db_path)
            with conn:
                conn.execute(
                    "INSERT INTO db_metadata (key, value) VALUES ('health_check_temp', ?);",
                    (datetime.datetime.now(datetime.timezone.utc).isoformat(),)
                )
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM db_metadata WHERE key='health_check_temp';")
                val = cursor.fetchone()["value"]
                assert val is not None
                conn.execute("DELETE FROM db_metadata WHERE key='health_check_temp';")
            checks["journal_read_write"] = "OK"
        except Exception as e:
            errors.append(f"Database journal write check failed: {str(e)}")
            checks["journal_read_write"] = "FAILED"
            
    # 3. Watchlist File Check
    if watchlist_path:
        if os.path.exists(watchlist_path):
            checks["watchlist_file"] = "OK"
        else:
            warnings.append(f"Watchlist file not found at {watchlist_path}.")
            checks["watchlist_file"] = "WARNING"
    else:
        checks["watchlist_file"] = "SKIPPED"
        
    # 4. Alert Provider Check
    discord_configured = bool(discord_webhook)
    tg_configured = bool(tg_bot_token)
    
    checks["discord_configured"] = "OK" if discord_configured else "WARNING"
    checks["telegram_configured"] = "OK" if tg_configured else "WARNING"
    
    if not discord_configured:
        warnings.append("Discord Webhook is not configured. Alerts on Discord will be skipped.")
    if not tg_configured:
        warnings.append("Telegram Bot Token is not configured. Alerts on Telegram will be skipped.")
        
    # 5. Determine Overall status
    if errors:
        status = "FAILED"
    elif warnings:
        status = "WARNING"
    else:
        status = "OK"
        
    return {
        "health_status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
