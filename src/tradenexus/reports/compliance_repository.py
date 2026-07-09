import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from tradenexus.journal.db import get_db_connection

logger = logging.getLogger(__name__)

def get_workspace_name(workspace_id: str, db_path: str = None) -> str:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT workspace_name FROM workspaces WHERE workspace_id = ?;", (workspace_id,))
        row = cursor.fetchone()
        if row:
            return row["workspace_name"]
        return "Unknown Workspace"
    except Exception as e:
        logger.error(f"Error fetching workspace name: {str(e)}")
        return workspace_id
    finally:
        conn.close()

def load_compliance_data(
    workspace_id: str,
    start_date: str,
    end_date: str,
    db_path: str = None
) -> Dict[str, Any]:
    """
    Loads all relevant records for a compliance report within the date range (inclusive).
    """
    conn = get_db_connection(db_path)
    data = {
        "signals": [],
        "alert_logs": [],
        "trades": [],
        "playbook_events": [],
        "risk_events": [],
        "recommendations": []
    }
    
    try:
        cursor = conn.cursor()
        
        # 1. Load Signals
        cursor.execute("""
            SELECT * FROM signals 
            WHERE workspace_id = ? AND candle_close_time >= ? AND candle_close_time <= ?
            ORDER BY candle_close_time ASC
        """, (workspace_id, start_date, end_date))
        data["signals"] = [dict(r) for r in cursor.fetchall()]
        
        # 2. Load Alert Logs
        cursor.execute("""
            SELECT * FROM alert_log 
            WHERE workspace_id = ? AND sent_at >= ? AND sent_at <= ?
            ORDER BY sent_at ASC
        """, (workspace_id, start_date, end_date))
        data["alert_logs"] = [dict(r) for r in cursor.fetchall()]
        
        # 3. Load Trades
        cursor.execute("""
            SELECT * FROM trades 
            WHERE workspace_id = ? AND opened_at >= ? AND opened_at <= ?
            ORDER BY opened_at ASC
        """, (workspace_id, start_date, end_date))
        data["trades"] = [dict(r) for r in cursor.fetchall()]
        
        # 4. Load Playbook rule events
        cursor.execute("""
            SELECT * FROM playbook_rule_events 
            WHERE workspace_id = ? AND created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
        """, (workspace_id, start_date, end_date))
        data["playbook_events"] = [dict(r) for r in cursor.fetchall()]
        
        # 5. Load Portfolio risk events
        cursor.execute("""
            SELECT * FROM portfolio_risk_events 
            WHERE workspace_id = ? AND created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
        """, (workspace_id, start_date, end_date))
        data["risk_events"] = [dict(r) for r in cursor.fetchall()]
        
        # 6. Load Parameter Recommendations
        cursor.execute("""
            SELECT * FROM parameter_recommendations 
            WHERE workspace_id = ?
            ORDER BY created_at DESC
        """, (workspace_id,))
        data["recommendations"] = [dict(r) for r in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error loading compliance data from DB: {str(e)}")
    finally:
        conn.close()
        
    return data
