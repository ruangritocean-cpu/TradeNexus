import json
import datetime
from typing import Dict, Any, List, Optional
from tradenexus.journal.db import get_db_connection

def save_optimization_run(
    run_id: str,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    train_window_bars: int,
    test_window_bars: int,
    step_bars: int,
    max_combinations: int,
    status: str,
    config_dict: Dict[str, Any],
    sampling_seed: int,
    sampling_method: str,
    total_combinations: int,
    evaluated_combinations: int,
    db_path: str = None,
    workspace_id: str = None
) -> None:
    """
    Inserts a new optimization run metadata record.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        conn.execute("""
            INSERT INTO optimization_runs (
                run_id, symbol, timeframe, start_date, end_date,
                train_window_bars, test_window_bars, step_bars, max_combinations,
                status, created_at, config_json, sampling_seed, sampling_method,
                grid_total_combinations, grid_evaluated_combinations, workspace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, symbol, timeframe, start_date, end_date,
            train_window_bars, test_window_bars, step_bars, max_combinations,
            status, created_at, json.dumps(config_dict), sampling_seed, sampling_method,
            total_combinations, evaluated_combinations, workspace_id
        ))
        conn.commit()
    finally:
        conn.close()

def update_optimization_run_status(
    run_id: str,
    status: str,
    completed_at: str = None,
    db_path: str = None
) -> None:
    """
    Updates the status and optional completion timestamp of an optimization run.
    """
    conn = get_db_connection(db_path)
    try:
        if completed_at:
            conn.execute("""
                UPDATE optimization_runs 
                SET status = ?, completed_at = ? 
                WHERE run_id = ?
            """, (status, completed_at, run_id))
        else:
            conn.execute("""
                UPDATE optimization_runs 
                SET status = ? 
                WHERE run_id = ?
            """, (status, run_id))
        conn.commit()
    finally:
        conn.close()

def save_optimization_result(
    run_id: str,
    window_index: int,
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    params_dict: Dict[str, Any],
    in_sample_metrics: Dict[str, Any],
    out_sample_metrics: Dict[str, Any],
    robustness_score: float,
    warnings: List[str],
    db_path: str = None,
    workspace_id: str = None
) -> None:
    """
    Saves a walk-forward window slice result.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        conn.execute("""
            INSERT INTO optimization_results (
                run_id, window_index, train_start, train_end, test_start, test_end,
                params_json, in_sample_metrics_json, out_sample_metrics_json,
                robustness_score, warnings_json, workspace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, window_index, train_start, train_end, test_start, test_end,
            json.dumps(params_dict), json.dumps(in_sample_metrics), json.dumps(out_sample_metrics),
            robustness_score, json.dumps(warnings), workspace_id
        ))
        conn.commit()
    finally:
        conn.close()

def save_parameter_recommendation(
    recommendation_id: str,
    symbol: str,
    timeframe: str,
    params_dict: Dict[str, Any],
    robustness_score: float,
    sample_size: int,
    recommendation_status: str,
    valid_from: str,
    notes: str = "",
    db_path: str = None,
    workspace_id: str = None
) -> None:
    """
    Saves a final strategy parameters recommendation.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO parameter_recommendations (
                recommendation_id, symbol, timeframe, params_json,
                robustness_score, sample_size, recommendation_status,
                valid_from, created_at, notes, workspace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation_id, symbol, timeframe, json.dumps(params_dict),
            robustness_score, sample_size, recommendation_status,
            valid_from, created_at, notes, workspace_id
        ))
        conn.commit()
    finally:
        conn.close()

def load_optimization_runs(
    limit: int = 10,
    db_path: str = None,
    workspace_id: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieves latest optimization runs sorted by creation time.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM optimization_runs 
            WHERE workspace_id = ?
            ORDER BY created_at DESC 
            LIMIT ?
        """, (workspace_id, limit))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def load_optimization_results(
    run_id: str,
    db_path: str = None,
    workspace_id: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieves all walk-forward window index results for a given run ID.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM optimization_results 
            WHERE run_id = ? AND workspace_id = ?
            ORDER BY window_index ASC
        """, (run_id, workspace_id))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def load_parameter_recommendations(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    db_path: str = None,
    workspace_id: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieves parameter recommendations.
    Can be filtered by symbol and/or timeframe.
    """
    if workspace_id is None:
        from tradenexus.workspace.workspace_context import get_active_workspace_id
        workspace_id = get_active_workspace_id()

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if symbol and timeframe:
            cursor.execute("""
                SELECT * FROM parameter_recommendations 
                WHERE symbol = ? AND timeframe = ? AND workspace_id = ?
                ORDER BY created_at DESC
            """, (symbol, timeframe, workspace_id))
        elif symbol:
            cursor.execute("""
                SELECT * FROM parameter_recommendations 
                WHERE symbol = ? AND workspace_id = ?
                ORDER BY created_at DESC
            """, (symbol, workspace_id))
        else:
            cursor.execute("""
                SELECT * FROM parameter_recommendations 
                WHERE workspace_id = ?
                ORDER BY created_at DESC
            """, (workspace_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
