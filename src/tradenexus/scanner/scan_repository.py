import sqlite3
import json
import logging
from typing import List, Optional
from tradenexus.journal.db import get_db_connection
from tradenexus.scanner.scan_models import ScanRun, ScanResult

logger = logging.getLogger(__name__)

def _get_row_val(r, col, default):
    try:
        val = r[col]
        return val if val is not None else default
    except (IndexError, KeyError, sqlite3.IndexError, sqlite3.OperationalError):
        return default

def insert_scan_run(scan_run: ScanRun, db_path: str = None, workspace_id: str = None) -> bool:
    if workspace_id is None:
        workspace_id = getattr(scan_run, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO scan_runs (
                    scan_run_id, started_at, finished_at, status,
                    total_symbols, success_count, warning_count, error_count, skipped_count, config_json, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_run.scan_run_id,
                    scan_run.started_at,
                    scan_run.finished_at,
                    scan_run.status,
                    scan_run.total_symbols,
                    scan_run.success_count,
                    scan_run.warning_count,
                    scan_run.error_count,
                    scan_run.skipped_count,
                    scan_run.config_json,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error inserting scan run: {str(e)}")
        return False
    finally:
        conn.close()

def insert_scan_result(result: ScanResult, db_path: str = None, workspace_id: str = None) -> bool:
    if workspace_id is None:
        workspace_id = getattr(result, "workspace_id", None)
    if not workspace_id:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO scan_results (
                    scan_run_id, signal_id, symbol, timeframe, scan_time, symbol_status,
                    decision_state, direction, alignment_type, confluence_score, rr_tp1,
                    primary_regime, regime_flags_json, data_quality_status, alert_status,
                    journal_status, reasons_json, warnings_json, error_message, created_at,
                    position_size_units, candidate_risk_amount, candidate_risk_pct,
                    provider_used, fallback_used, data_quality_warnings_json, data_quality_errors_json,
                    latest_candle_time, bars_available, workspace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scan_run_id,
                    result.signal_id,
                    result.symbol,
                    result.timeframe,
                    result.scan_time,
                    result.symbol_status,
                    result.decision_state,
                    result.direction,
                    result.alignment_type,
                    result.confluence_score,
                    result.rr_tp1,
                    result.primary_regime,
                    result.regime_flags_json,
                    result.data_quality_status,
                    result.alert_status,
                    result.journal_status,
                    result.reasons_json,
                    result.warnings_json,
                    result.error_message,
                    result.created_at,
                    result.position_size_units,
                    result.candidate_risk_amount,
                    result.candidate_risk_pct,
                    result.provider_used,
                    result.fallback_used,
                    result.data_quality_warnings_json,
                    result.data_quality_errors_json,
                    result.latest_candle_time,
                    result.bars_available,
                    workspace_id
                )
            )
        return True
    except Exception as e:
        logger.error(f"Error inserting scan result: {str(e)}")
        return False
    finally:
        conn.close()

def load_scan_runs(limit: int = 50, offset: int = 0, db_path: str = None, workspace_id: str = None) -> List[ScanRun]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    runs = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scan_runs WHERE workspace_id = ? ORDER BY started_at DESC LIMIT ? OFFSET ?", (workspace_id, limit, offset))
        rows = cursor.fetchall()
        for r in rows:
            runs.append(ScanRun(
                scan_run_id=r["scan_run_id"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                status=r["status"],
                total_symbols=r["total_symbols"],
                success_count=r["success_count"],
                warning_count=r["warning_count"],
                error_count=r["error_count"],
                skipped_count=r["skipped_count"],
                config_json=r["config_json"],
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
    except Exception as e:
        logger.error(f"Error loading scan runs: {str(e)}")
    finally:
        conn.close()
    return runs

def load_scan_results_for_run(scan_run_id: str, db_path: str = None, workspace_id: str = None) -> List[ScanResult]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    results = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scan_results WHERE scan_run_id = ? AND workspace_id = ? ORDER BY symbol ASC", (scan_run_id, workspace_id))
        rows = cursor.fetchall()
        for r in rows:
            results.append(ScanResult(
                scan_run_id=r["scan_run_id"],
                signal_id=_get_row_val(r, "signal_id", None),
                symbol=r["symbol"],
                timeframe=r["timeframe"],
                scan_time=r["scan_time"],
                symbol_status=r["symbol_status"],
                decision_state=r["decision_state"],
                direction=r["direction"],
                alignment_type=r["alignment_type"],
                confluence_score=r["confluence_score"],
                rr_tp1=r["rr_tp1"],
                primary_regime=r["primary_regime"],
                regime_flags_json=r["regime_flags_json"],
                data_quality_status=r["data_quality_status"],
                alert_status=r["alert_status"],
                journal_status=r["journal_status"],
                reasons_json=r["reasons_json"],
                warnings_json=r["warnings_json"],
                error_message=r["error_message"],
                created_at=r["created_at"],
                id=r["id"],
                position_size_units=_get_row_val(r, "position_size_units", 0.0),
                candidate_risk_amount=_get_row_val(r, "candidate_risk_amount", 0.0),
                candidate_risk_pct=_get_row_val(r, "candidate_risk_pct", 0.0),
                provider_used=_get_row_val(r, "provider_used", "unknown"),
                fallback_used=_get_row_val(r, "fallback_used", 0),
                data_quality_warnings_json=_get_row_val(r, "data_quality_warnings_json", "[]"),
                data_quality_errors_json=_get_row_val(r, "data_quality_errors_json", "[]"),
                latest_candle_time=_get_row_val(r, "latest_candle_time", None),
                bars_available=_get_row_val(r, "bars_available", 0),
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
    except Exception as e:
        logger.error(f"Error loading scan results for run: {str(e)}")
    finally:
        conn.close()
    return results

def load_scan_results_paginated(limit: int = 50, offset: int = 0, db_path: str = None, workspace_id: str = None) -> List[ScanResult]:
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    results = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scan_results WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (workspace_id, limit, offset))
        rows = cursor.fetchall()
        for r in rows:
            results.append(ScanResult(
                scan_run_id=r["scan_run_id"],
                signal_id=_get_row_val(r, "signal_id", None),
                symbol=r["symbol"],
                timeframe=r["timeframe"],
                scan_time=r["scan_time"],
                symbol_status=r["symbol_status"],
                decision_state=r["decision_state"],
                direction=r["direction"],
                alignment_type=r["alignment_type"],
                confluence_score=r["confluence_score"],
                rr_tp1=r["rr_tp1"],
                primary_regime=r["primary_regime"],
                regime_flags_json=r["regime_flags_json"],
                data_quality_status=r["data_quality_status"],
                alert_status=r["alert_status"],
                journal_status=r["journal_status"],
                reasons_json=r["reasons_json"],
                warnings_json=r["warnings_json"],
                error_message=r["error_message"],
                created_at=r["created_at"],
                id=r["id"],
                position_size_units=_get_row_val(r, "position_size_units", 0.0),
                candidate_risk_amount=_get_row_val(r, "candidate_risk_amount", 0.0),
                candidate_risk_pct=_get_row_val(r, "candidate_risk_pct", 0.0),
                provider_used=_get_row_val(r, "provider_used", "unknown"),
                fallback_used=_get_row_val(r, "fallback_used", 0),
                data_quality_warnings_json=_get_row_val(r, "data_quality_warnings_json", "[]"),
                data_quality_errors_json=_get_row_val(r, "data_quality_errors_json", "[]"),
                latest_candle_time=_get_row_val(r, "latest_candle_time", None),
                bars_available=_get_row_val(r, "bars_available", 0),
                workspace_id=r["workspace_id"] if "workspace_id" in r.keys() else "default_workspace"
            ))
    except Exception as e:
        logger.error(f"Error loading paginated scan results: {str(e)}")
    finally:
        conn.close()
    return results
