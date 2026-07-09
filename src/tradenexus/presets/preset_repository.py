import sqlite3
import json
import datetime
import uuid
from typing import List, Optional
from tradenexus.journal.db import get_db_connection
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord

def _row_to_preset(r) -> StrategyPreset:
    return StrategyPreset(
        preset_id=r["preset_id"],
        workspace_id=r["workspace_id"],
        name=r["name"],
        description=r["description"],
        asset_class=r["asset_class"],
        trading_style=r["trading_style"],
        risk_profile=r["risk_profile"],
        allowed_symbols=json.loads(r["allowed_symbols_json"]) if r["allowed_symbols_json"] else [],
        allowed_timeframes=json.loads(r["allowed_timeframes_json"]) if r["allowed_timeframes_json"] else [],
        allowed_sessions=json.loads(r["allowed_sessions_json"]) if r["allowed_sessions_json"] else [],
        allowed_setup_types=json.loads(r["allowed_setup_types_json"]) if r["allowed_setup_types_json"] else [],
        allowed_regimes=json.loads(r["allowed_regimes_json"]) if r["allowed_regimes_json"] else [],
        blocked_regimes=json.loads(r["blocked_regimes_json"]) if r["blocked_regimes_json"] else [],
        min_confluence_score=r["min_confluence_score"],
        min_rr=r["min_rr"],
        max_trades_per_day=r["max_trades_per_day"],
        max_losses_per_day=r["max_losses_per_day"],
        max_consecutive_losses=r["max_consecutive_losses"],
        cooldown_minutes_after_loss=r["cooldown_minutes_after_loss"],
        default_portfolio_risk_pct=r["default_portfolio_risk_pct"],
        suggested_symbols=json.loads(r["suggested_symbols_json"]) if r["suggested_symbols_json"] else [],
        notes=r["notes"],
        tags=json.loads(r["tags_json"]) if r["tags_json"] else [],
        is_builtin=r["is_builtin"],
        created_at=r["created_at"],
        updated_at=r["updated_at"]
    )

def load_preset(preset_id: str, workspace_id: str, db_path: str = None) -> Optional[StrategyPreset]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        # First attempt to load workspace-specific preset
        cursor.execute(
            "SELECT * FROM strategy_presets WHERE preset_id = ? AND workspace_id = ?;",
            (preset_id, workspace_id)
        )
        row = cursor.fetchone()
        if row:
            return _row_to_preset(row)
            
        # Fallback to built-in preset
        cursor.execute(
            "SELECT * FROM strategy_presets WHERE preset_id = ? AND workspace_id = '__builtin__';",
            (preset_id,)
        )
        row_builtin = cursor.fetchone()
        if row_builtin:
            return _row_to_preset(row_builtin)
            
        return None
    finally:
        conn.close()

def load_all_presets(workspace_id: str, db_path: str = None) -> List[StrategyPreset]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM strategy_presets WHERE workspace_id = ? OR workspace_id = '__builtin__';",
            (workspace_id,)
        )
        rows = cursor.fetchall()
        # Filter duplicates (if a custom preset overrides a builtin ID)
        presets_map = {}
        for r in rows:
            p = _row_to_preset(r)
            # Custom presets have priority
            if p.preset_id not in presets_map or p.workspace_id != "__builtin__":
                presets_map[p.preset_id] = p
        return list(presets_map.values())
    finally:
        conn.close()

def load_builtin_presets(db_path: str = None) -> List[StrategyPreset]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM strategy_presets WHERE workspace_id = '__builtin__';")
        return [_row_to_preset(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def load_workspace_presets(workspace_id: str, db_path: str = None) -> List[StrategyPreset]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM strategy_presets WHERE workspace_id = ?;", (workspace_id,))
        return [_row_to_preset(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def save_preset(preset: StrategyPreset, workspace_id: str, db_path: str = None) -> bool:
    if workspace_id == "__builtin__" or preset.is_builtin == 1:
        # Built-in presets are read-only
        return False
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_builtin FROM strategy_presets WHERE preset_id = ? AND workspace_id = '__builtin__';",
            (preset.preset_id,)
        )
        if cursor.fetchone():
            return False
            
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO strategy_presets (
                    preset_id, workspace_id, name, description, asset_class, trading_style, risk_profile,
                    allowed_symbols_json, allowed_timeframes_json, allowed_sessions_json, allowed_setup_types_json,
                    allowed_regimes_json, blocked_regimes_json, min_confluence_score, min_rr, max_trades_per_day,
                    max_losses_per_day, max_consecutive_losses, cooldown_minutes_after_loss, default_portfolio_risk_pct,
                    suggested_symbols_json, notes, tags_json, is_builtin, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                preset.preset_id,
                workspace_id,
                preset.name,
                preset.description,
                preset.asset_class,
                preset.trading_style,
                preset.risk_profile,
                json.dumps(preset.allowed_symbols),
                json.dumps(preset.allowed_timeframes),
                json.dumps(preset.allowed_sessions),
                json.dumps(preset.allowed_setup_types),
                json.dumps(preset.allowed_regimes),
                json.dumps(preset.blocked_regimes),
                preset.min_confluence_score,
                preset.min_rr,
                preset.max_trades_per_day,
                preset.max_losses_per_day,
                preset.max_consecutive_losses,
                preset.cooldown_minutes_after_loss,
                preset.default_portfolio_risk_pct,
                json.dumps(preset.suggested_symbols),
                preset.notes,
                json.dumps(preset.tags),
                0, # is_builtin is always 0 for workspace custom presets
                preset.created_at or now_str,
                now_str
            ))
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_preset(preset_id: str, workspace_id: str, db_path: str = None) -> bool:
    if workspace_id == "__builtin__":
        return False
        
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            # Double check if builtin
            cursor.execute(
                "SELECT is_builtin FROM strategy_presets WHERE preset_id = ?;",
                (preset_id,)
            )
            rows = cursor.fetchall()
            if any(r["is_builtin"] == 1 for r in rows):
                return False
                
            # Check if exists
            cursor.execute(
                "SELECT preset_id FROM strategy_presets WHERE preset_id = ? AND workspace_id = ?;",
                (preset_id, workspace_id)
            )
            row = cursor.fetchone()
            if not row:
                return False
                
            conn.execute(
                "DELETE FROM strategy_presets WHERE preset_id = ? AND workspace_id = ?;",
                (preset_id, workspace_id)
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()

def duplicate_builtin_preset(preset_id: str, target_workspace_id: str, db_path: str = None) -> Optional[StrategyPreset]:
    preset = load_preset(preset_id, target_workspace_id, db_path)
    if not preset:
        return None
        
    new_preset = StrategyPreset(
        preset_id=f"custom_{preset_id}_{str(uuid.uuid4())[:8]}",
        workspace_id=target_workspace_id,
        name=f"Copy of {preset.name}",
        description=preset.description,
        asset_class=preset.asset_class,
        trading_style=preset.trading_style,
        risk_profile=preset.risk_profile,
        allowed_symbols=list(preset.allowed_symbols),
        allowed_timeframes=list(preset.allowed_timeframes),
        allowed_sessions=list(preset.allowed_sessions),
        allowed_setup_types=list(preset.allowed_setup_types),
        allowed_regimes=list(preset.allowed_regimes),
        blocked_regimes=list(preset.blocked_regimes),
        min_confluence_score=preset.min_confluence_score,
        min_rr=preset.min_rr,
        max_trades_per_day=preset.max_trades_per_day,
        max_losses_per_day=preset.max_losses_per_day,
        max_consecutive_losses=preset.max_consecutive_losses,
        cooldown_minutes_after_loss=preset.cooldown_minutes_after_loss,
        default_portfolio_risk_pct=preset.default_portfolio_risk_pct,
        suggested_symbols=list(preset.suggested_symbols),
        notes=preset.notes,
        tags=list(preset.tags) + ["Custom"],
        is_builtin=0,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    if save_preset(new_preset, target_workspace_id, db_path):
        return new_preset
    return None

def load_apply_history(workspace_id: str, db_path: str = None) -> List[PresetApplyRecord]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM preset_apply_history WHERE workspace_id = ? ORDER BY applied_at DESC;",
            (workspace_id,)
        )
        rows = cursor.fetchall()
        records = []
        for r in rows:
            records.append(PresetApplyRecord(
                apply_id=r["apply_id"],
                preset_id=r["preset_id"],
                workspace_id=r["workspace_id"],
                applied_at=r["applied_at"],
                applied_sections=json.loads(r["applied_sections_json"]) if r["applied_sections_json"] else [],
                previous_values=r["previous_values_json"],
                new_values=r["new_values_json"],
                warnings=json.loads(r["warnings_json"]) if r["warnings_json"] else [],
                applied_by_label=r["applied_by_label"]
            ))
        return records
    finally:
        conn.close()

def log_apply_history(record: PresetApplyRecord, db_path: str = None) -> bool:
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO preset_apply_history (
                    apply_id, preset_id, workspace_id, applied_at, applied_sections_json,
                    previous_values_json, new_values_json, warnings_json, applied_by_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                record.apply_id,
                record.preset_id,
                record.workspace_id,
                record.applied_at,
                json.dumps(record.applied_sections),
                record.previous_values,
                record.new_values,
                json.dumps(record.warnings),
                record.applied_by_label
            ))
        return True
    except Exception:
        return False
    finally:
        conn.close()
