import sqlite3
import json
import datetime
from typing import List, Optional
from tradenexus.playbook.playbook_models import Playbook, PlaybookRuleEvent, DailyTradingState
from tradenexus.journal.db import get_db_connection

DEFAULT_DB = "data/tradenexus_journal.sqlite"

def save_playbook(playbook: Playbook, db_path: str = None, workspace_id: str = None):
    if workspace_id is None:
        workspace_id = getattr(playbook, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO playbooks (
                    playbook_id, name, enabled, allowed_symbols, allowed_asset_classes,
                    allowed_timeframes, allowed_setup_types, min_confluence_score, min_rr,
                    allowed_regimes, blocked_regimes, max_trades_per_day, max_losses_per_day,
                    max_consecutive_losses, allowed_sessions, cooldown_minutes_after_loss,
                    created_at, notes, workspace_id, active_preset_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                playbook.playbook_id,
                playbook.name,
                playbook.enabled,
                json.dumps(playbook.allowed_symbols),
                json.dumps(playbook.allowed_asset_classes),
                json.dumps(playbook.allowed_timeframes),
                json.dumps(playbook.allowed_setup_types),
                playbook.min_confluence_score,
                playbook.min_rr,
                json.dumps(playbook.allowed_regimes),
                json.dumps(playbook.blocked_regimes),
                playbook.max_trades_per_day,
                playbook.max_losses_per_day,
                playbook.max_consecutive_losses,
                json.dumps(playbook.allowed_sessions),
                playbook.cooldown_minutes_after_loss,
                playbook.created_at or datetime.datetime.now().isoformat(),
                playbook.notes,
                workspace_id,
                playbook.active_preset_id
            ))
    finally:
        conn.close()

def load_playbooks(db_path: str = None, workspace_id: str = None) -> List[Playbook]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playbooks';")
        if not cursor.fetchone():
            return []
            
        cursor.execute("SELECT * FROM playbooks WHERE workspace_id = ? ORDER BY created_at DESC;", (workspace_id,))
        rows = cursor.fetchall()
        
        playbooks = []
        for r in rows:
            playbooks.append(Playbook(
                playbook_id=r["playbook_id"],
                name=r["name"],
                enabled=r["enabled"],
                allowed_symbols=json.loads(r["allowed_symbols"]) if r["allowed_symbols"] else [],
                allowed_asset_classes=json.loads(r["allowed_asset_classes"]) if r["allowed_asset_classes"] else [],
                allowed_timeframes=json.loads(r["allowed_timeframes"]) if r["allowed_timeframes"] else [],
                allowed_setup_types=json.loads(r["allowed_setup_types"]) if r["allowed_setup_types"] else [],
                min_confluence_score=r["min_confluence_score"],
                min_rr=r["min_rr"],
                allowed_regimes=json.loads(r["allowed_regimes"]) if r["allowed_regimes"] else [],
                blocked_regimes=json.loads(r["blocked_regimes"]) if r["blocked_regimes"] else [],
                max_trades_per_day=r["max_trades_per_day"],
                max_losses_per_day=r["max_losses_per_day"],
                max_consecutive_losses=r["max_consecutive_losses"],
                allowed_sessions=json.loads(r["allowed_sessions"]) if r["allowed_sessions"] else [],
                cooldown_minutes_after_loss=r["cooldown_minutes_after_loss"],
                created_at=r["created_at"],
                notes=r["notes"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace",
                active_preset_id=r["active_preset_id"] if "active_preset_id" in r.keys() else None
            ))
        return playbooks
    finally:
        conn.close()

def get_active_playbook(db_path: str = None, workspace_id: str = None) -> Optional[Playbook]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    playbooks = load_playbooks(db_path, workspace_id)
    enabled_playbooks = [p for p in playbooks if p.enabled == 1]
    if enabled_playbooks:
        return enabled_playbooks[0]
        
    # If none is enabled/exists, create default
    if not playbooks:
        default_pb = Playbook(
            playbook_id="default_playbook",
            name="Default Aggressive Playbook",
            enabled=1,
            allowed_symbols=["BTC-USD", "ETH-USD", "AAPL", "MSFT", "^IXIC", "GOOG"],
            allowed_timeframes=["15m", "1h", "4h", "1d"],
            allowed_setup_types=["TREND_FOLLOWING", "COUNTER_TREND_SCALP"],
            min_confluence_score=70.0,
            min_rr=1.5,
            allowed_sessions=["ASIAN", "LONDON", "NEWYORK"],
            notes="Default system-generated trading playbook.",
            workspace_id=workspace_id
        )
        save_playbook(default_pb, db_path, workspace_id)
        return default_pb
    return playbooks[0]

def set_playbook_enabled(playbook_id: str, enabled: int, db_path: str = None, workspace_id: str = None):
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            if enabled == 1:
                conn.execute("UPDATE playbooks SET enabled = 0 WHERE workspace_id = ?;", (workspace_id,))
            conn.execute("UPDATE playbooks SET enabled = ? WHERE playbook_id = ? AND workspace_id = ?;", (enabled, playbook_id, workspace_id))
    finally:
        conn.close()

def log_playbook_rule_event(event: PlaybookRuleEvent, db_path: str = None, workspace_id: str = None):
    if workspace_id is None:
        workspace_id = getattr(event, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO playbook_rule_events (
                    event_id, created_at, playbook_id, symbol, rule_name, event_type, decision_state, details_json, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                event.event_id,
                event.created_at,
                event.playbook_id,
                event.symbol,
                event.rule_name,
                event.event_type,
                event.decision_state,
                event.details_json,
                workspace_id
            ))
    finally:
        conn.close()

def load_playbook_rule_events(limit: int = 50, db_path: str = None, workspace_id: str = None) -> List[PlaybookRuleEvent]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playbook_rule_events';")
        if not cursor.fetchone():
            return []
            
        cursor.execute("SELECT * FROM playbook_rule_events WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?;", (workspace_id, limit))
        rows = cursor.fetchall()
        events = []
        for r in rows:
            events.append(PlaybookRuleEvent(
                event_id=r["event_id"],
                created_at=r["created_at"],
                playbook_id=r["playbook_id"],
                symbol=r["symbol"],
                rule_name=r["rule_name"],
                event_type=r["event_type"],
                decision_state=r["decision_state"],
                details_json=r["details_json"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
        return events
    finally:
        conn.close()

def get_daily_trading_state(date_str: str, db_path: str = None, workspace_id: str = None) -> DailyTradingState:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_trading_state';")
        if not cursor.fetchone():
            return DailyTradingState(date=date_str, workspace_id=workspace_id)
            
        cursor.execute("SELECT * FROM daily_trading_state WHERE date = ? AND workspace_id = ?;", (date_str, workspace_id))
        row = cursor.fetchone()
        if row:
            return DailyTradingState(
                date=row["date"],
                trades_count=row["trades_count"],
                losses_count=row["losses_count"],
                consecutive_losses=row["consecutive_losses"],
                last_loss_time=row["last_loss_time"],
                updated_at=row["updated_at"],
                workspace_id=row["workspace_id"] if "workspace_id" in row.keys() else "default_workspace"
            )
        state = DailyTradingState(date=date_str, workspace_id=workspace_id)
        save_daily_trading_state(state, db_path, workspace_id)
        return state
    finally:
        conn.close()

def save_daily_trading_state(state: DailyTradingState, db_path: str = None, workspace_id: str = None):
    if workspace_id is None:
        workspace_id = getattr(state, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_trading_state (
                    date, trades_count, losses_count, consecutive_losses, last_loss_time, updated_at, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                state.date,
                state.trades_count,
                state.losses_count,
                state.consecutive_losses,
                state.last_loss_time,
                datetime.datetime.now().isoformat(),
                workspace_id
            ))
    finally:
        conn.close()
