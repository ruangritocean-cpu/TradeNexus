import sqlite3
import json
import logging
import datetime
from typing import List, Optional
from tradenexus.journal.db import get_db_connection
from tradenexus.portfolio.risk_models import PortfolioSettings, SymbolRiskProfile, PortfolioSnapshot, PortfolioRiskEvent

logger = logging.getLogger(__name__)

def _get_row_val(r, col, default):
    try:
        val = r[col]
        return val if val is not None else default
    except (IndexError, KeyError, sqlite3.IndexError, sqlite3.OperationalError):
        return default

def load_portfolio_settings(db_path: str = None, workspace_id: str = None) -> PortfolioSettings:
    """
    Loads portfolio settings from database for the active workspace.
    Creates default row if database is empty.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_settings WHERE workspace_id = ? LIMIT 1", (workspace_id,))
        r = cursor.fetchone()
        if r:
            return PortfolioSettings(
                id=r["id"],
                account_equity=r["account_equity"],
                risk_per_trade_pct=r["risk_per_trade_pct"],
                max_daily_risk_pct=r["max_daily_risk_pct"],
                max_total_open_risk_pct=r["max_total_open_risk_pct"],
                max_concurrent_trades=r["max_concurrent_trades"],
                max_same_direction_trades=r["max_same_direction_trades"],
                max_correlated_positions=r["max_correlated_positions"],
                correlation_threshold=r["correlation_threshold"],
                correlation_lookback_bars=r["correlation_lookback_bars"],
                correlation_cache_ttl_seconds=r["correlation_cache_ttl_seconds"],
                default_contract_multiplier=r["default_contract_multiplier"],
                default_point_value=r["default_point_value"],
                currency=r["currency"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            )
        else:
            # Create default row
            default_settings = PortfolioSettings(workspace_id=workspace_id)
            save_portfolio_settings(default_settings, db_path, workspace_id)
            return default_settings
    except Exception as e:
        logger.error(f"Error loading portfolio settings: {str(e)}")
        return PortfolioSettings(workspace_id=workspace_id)
    finally:
        conn.close()

def save_portfolio_settings(settings: PortfolioSettings, db_path: str = None, workspace_id: str = None) -> bool:
    """
    Saves portfolio settings to the database for the active workspace.
    """
    if workspace_id is None:
        workspace_id = getattr(settings, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_settings (
                    id, account_equity, risk_per_trade_pct, max_daily_risk_pct,
                    max_total_open_risk_pct, max_concurrent_trades, max_same_direction_trades,
                    max_correlated_positions, correlation_threshold, correlation_lookback_bars,
                    correlation_cache_ttl_seconds, default_contract_multiplier, default_point_value,
                    currency, updated_at, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    settings.id,
                    settings.account_equity,
                    settings.risk_per_trade_pct,
                    settings.max_daily_risk_pct,
                    settings.max_total_open_risk_pct,
                    settings.max_concurrent_trades,
                    settings.max_same_direction_trades,
                    settings.max_correlated_positions,
                    settings.correlation_threshold,
                    settings.correlation_lookback_bars,
                    settings.correlation_cache_ttl_seconds,
                    settings.default_contract_multiplier,
                    settings.default_point_value,
                    settings.currency,
                    now_utc,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error saving portfolio settings: {str(e)}")
        return False
    finally:
        conn.close()

def load_symbol_profile(symbol: str, db_path: str = None, workspace_id: str = None) -> Optional[SymbolRiskProfile]:
    """
    Loads symbol specific risk settings for the active workspace.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_symbol_profiles WHERE symbol = ? AND workspace_id = ?", (symbol, workspace_id))
        r = cursor.fetchone()
        if r:
            return SymbolRiskProfile(
                symbol=r["symbol"],
                asset_class=r["asset_class"],
                point_value=r["point_value"],
                contract_multiplier=r["contract_multiplier"],
                min_position_size=r["min_position_size"],
                position_step=r["position_step"],
                currency=r["currency"],
                updated_at=r["updated_at"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            )
        return None
    except Exception as e:
        logger.error(f"Error loading symbol profile: {str(e)}")
        return None
    finally:
        conn.close()

def save_symbol_profile(profile: SymbolRiskProfile, db_path: str = None, workspace_id: str = None) -> bool:
    """
    Saves or overrides symbol risk profile for the active workspace.
    """
    if workspace_id is None:
        workspace_id = getattr(profile, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_symbol_profiles (
                    symbol, asset_class, point_value, contract_multiplier,
                    min_position_size, position_step, currency, updated_at, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.symbol,
                    profile.asset_class,
                    profile.point_value,
                    profile.contract_multiplier,
                    profile.min_position_size,
                    profile.position_step,
                    profile.currency,
                    now_utc,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error saving symbol profile: {str(e)}")
        return False
    finally:
        conn.close()

def load_all_symbol_profiles(db_path: str = None, workspace_id: str = None) -> List[SymbolRiskProfile]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    profiles = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_symbol_profiles WHERE workspace_id = ? ORDER BY symbol ASC", (workspace_id,))
        rows = cursor.fetchall()
        for r in rows:
            profiles.append(SymbolRiskProfile(
                symbol=r["symbol"],
                asset_class=r["asset_class"],
                point_value=r["point_value"],
                contract_multiplier=r["contract_multiplier"],
                min_position_size=r["min_position_size"],
                position_step=r["position_step"],
                currency=r["currency"],
                updated_at=r["updated_at"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
    except Exception as e:
        logger.error(f"Error loading all symbol profiles: {str(e)}")
    finally:
        conn.close()
    return profiles

def insert_portfolio_snapshot(snapshot: PortfolioSnapshot, db_path: str = None, workspace_id: str = None) -> bool:
    if workspace_id is None:
        workspace_id = getattr(snapshot, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO portfolio_snapshots (
                    snapshot_id, created_at, realized_daily_risk, open_risk,
                    open_risk_pct, potential_setup_risk, potential_setup_risk_pct,
                    active_trade_count, actionable_setup_count, risk_status,
                    warnings_json, details_json, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.created_at,
                    snapshot.realized_daily_risk,
                    snapshot.open_risk,
                    snapshot.open_risk_pct,
                    snapshot.potential_setup_risk,
                    snapshot.potential_setup_risk_pct,
                    snapshot.active_trade_count,
                    snapshot.actionable_setup_count,
                    snapshot.risk_status,
                    snapshot.warnings_json,
                    snapshot.details_json,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error inserting portfolio snapshot: {str(e)}")
        return False
    finally:
        conn.close()

def insert_risk_event(event: PortfolioRiskEvent, db_path: str = None, workspace_id: str = None) -> bool:
    if workspace_id is None:
        workspace_id = getattr(event, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO portfolio_risk_events (
                    event_id, created_at, signal_id, trade_id, symbol,
                    event_type, risk_status, reason, details_json, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.created_at,
                    event.signal_id,
                    event.trade_id,
                    event.symbol,
                    event.event_type,
                    event.risk_status,
                    event.reason,
                    event.details_json,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error inserting risk event: {str(e)}")
        return False
    finally:
        conn.close()

def load_risk_events(limit: int = 50, offset: int = 0, db_path: str = None, workspace_id: str = None) -> List[PortfolioRiskEvent]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    events = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio_risk_events WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (workspace_id, limit, offset))
        rows = cursor.fetchall()
        for r in rows:
            events.append(PortfolioRiskEvent(
                event_id=r["event_id"],
                created_at=r["created_at"],
                signal_id=_get_row_val(r, "signal_id", None),
                trade_id=_get_row_val(r, "trade_id", None),
                symbol=r["symbol"],
                event_type=r["event_type"],
                risk_status=r["risk_status"],
                reason=r["reason"],
                details_json=r["details_json"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
    except Exception as e:
        logger.error(f"Error loading risk events: {str(e)}")
    finally:
        conn.close()
    return events
