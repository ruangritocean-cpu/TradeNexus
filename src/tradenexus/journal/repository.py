import sqlite3
import hashlib
import json
import datetime
import logging
import io
import csv
from typing import List, Optional
from tradenexus.journal.db import get_db_connection
from tradenexus.journal.models import Signal, AlertLog, Trade

logger = logging.getLogger(__name__)

def _get_row_val(r, col, default):
    try:
        val = r[col]
        return val if val is not None else default
    except (IndexError, KeyError, sqlite3.IndexError, sqlite3.OperationalError):
        return default

def generate_signal_id(
    symbol: str,
    timeframe: str,
    candle_close_time: str,
    decision_state: str,
    direction: str,
    entry: float,
    sl: float,
    tp1: float
) -> str:
    """
    Generates a unique deterministic SHA256 signal_id based on normalized input fields.
    """
    # Normalize inputs
    norm_symbol = symbol.strip().upper()
    norm_tf = timeframe.strip().lower()
    norm_time = candle_close_time.strip()
    norm_state = decision_state.strip().upper()
    norm_dir = direction.strip().upper()
    
    # Round float parameters to 5 decimals for stability
    r_entry = round(entry, 5)
    r_sl = round(sl, 5)
    r_tp1 = round(tp1, 5)
    
    raw_str = f"{norm_symbol}_{norm_tf}_{norm_time}_{norm_state}_{norm_dir}_{r_entry:.5f}_{r_sl:.5f}_{r_tp1:.5f}"
    hasher = hashlib.sha256(raw_str.encode("utf-8"))
    return hasher.hexdigest()

def insert_signal(signal: Signal, db_path: str = None) -> bool:
    """
    Inserts a Signal dataclass into the SQLite database.
    Standardizes timestamps to timezone-aware UTC ISO format.
    """
    conn = get_db_connection(db_path)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO signals (
                    signal_id, symbol, timeframe, candle_close_time, decision_state,
                    direction, alignment_type, entry, sl, tp1, tp2, rr_tp1, rr_tp2,
                    confluence_score, directional_score, quality_score, market_bias,
                    setup_direction, trigger_direction, execution_direction,
                    smc_support_source, smc_resistance_source, data_quality_valid,
                    is_actionable, outcome_status, outcome_time, bars_to_outcome,
                    realized_r_multiple, reasons_json, warnings_json, created_at,
                    primary_regime, regime_flags, regime_score, volume_confirmation,
                    vwap_alignment, bos_present, choch_present, fvg_present,
                    liquidity_sweep_present
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                signal.signal_id, signal.symbol, signal.timeframe, signal.candle_close_time,
                signal.decision_state, signal.direction, signal.alignment_type,
                signal.entry, signal.sl, signal.tp1, signal.tp2, signal.rr_tp1, signal.rr_tp2,
                signal.confluence_score, signal.directional_score, signal.quality_score,
                signal.market_bias, signal.setup_direction, signal.trigger_direction,
                signal.execution_direction, signal.smc_support_source, signal.smc_resistance_source,
                signal.data_quality_valid, signal.is_actionable, signal.outcome_status,
                signal.outcome_time, signal.bars_to_outcome, signal.realized_r_multiple,
                json.dumps(signal.reasons), json.dumps(signal.warnings), now_str,
                signal.primary_regime, signal.regime_flags, signal.regime_score,
                signal.volume_confirmation, signal.vwap_alignment, signal.bos_present,
                signal.choch_present, signal.fvg_present, signal.liquidity_sweep_present
            ))
            inserted = cursor.rowcount > 0
        return inserted
    except Exception as e:
        logger.error(f"Error inserting signal {signal.signal_id}: {str(e)}")
        return False
    finally:
        conn.close()

def load_signals(db_path: str = None, actionable_only: bool = False) -> List[Signal]:
    """
    Loads all saved Signals from the database.
    """
    conn = get_db_connection(db_path)
    signals_list = []
    try:
        query = "SELECT * FROM signals ORDER BY candle_close_time DESC"
        if actionable_only:
            query = "SELECT * FROM signals WHERE is_actionable = 1 ORDER BY candle_close_time DESC"
            
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        for r in rows:
            reasons = []
            warnings = []
            try:
                reasons = json.loads(r["reasons_json"]) if r["reasons_json"] else []
                warnings = json.loads(r["warnings_json"]) if r["warnings_json"] else []
            except Exception:
                pass
                
            sig = Signal(
                signal_id=r["signal_id"],
                symbol=r["symbol"],
                timeframe=r["timeframe"],
                candle_close_time=r["candle_close_time"],
                decision_state=r["decision_state"],
                direction=r["direction"],
                alignment_type=r["alignment_type"],
                entry=r["entry"],
                sl=r["sl"],
                tp1=r["tp1"],
                tp2=r["tp2"],
                rr_tp1=r["rr_tp1"],
                rr_tp2=r["rr_tp2"],
                confluence_score=r["confluence_score"],
                directional_score=r["directional_score"],
                quality_score=r["quality_score"],
                market_bias=r["market_bias"],
                setup_direction=r["setup_direction"],
                trigger_direction=r["trigger_direction"],
                execution_direction=r["execution_direction"],
                smc_support_source=r["smc_support_source"],
                smc_resistance_source=r["smc_resistance_source"],
                data_quality_valid=r["data_quality_valid"],
                is_actionable=r["is_actionable"],
                reasons=reasons,
                warnings=warnings,
                outcome_status=r["outcome_status"],
                outcome_time=r["outcome_time"],
                bars_to_outcome=r["bars_to_outcome"],
                realized_r_multiple=r["realized_r_multiple"],
                created_at=r["created_at"],
                primary_regime=_get_row_val(r, "primary_regime", "UNKNOWN"),
                regime_flags=_get_row_val(r, "regime_flags", ""),
                regime_score=_get_row_val(r, "regime_score", 0.0),
                volume_confirmation=_get_row_val(r, "volume_confirmation", "NEUTRAL"),
                vwap_alignment=_get_row_val(r, "vwap_alignment", "NEUTRAL"),
                bos_present=_get_row_val(r, "bos_present", 0),
                choch_present=_get_row_val(r, "choch_present", 0),
                fvg_present=_get_row_val(r, "fvg_present", 0),
                liquidity_sweep_present=_get_row_val(r, "liquidity_sweep_present", 0)
            )
            signals_list.append(sig)
    except Exception as e:
        logger.error(f"Error loading signals: {str(e)}")
    finally:
        conn.close()
    return signals_list

def load_signals_paginated(limit: int, offset: int, db_path: str = None) -> List[Signal]:
    """
    Loads page-limited signals for UI performance.
    """
    conn = get_db_connection(db_path)
    signals_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY candle_close_time DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        for r in rows:
            reasons = []
            warnings = []
            try:
                reasons = json.loads(r["reasons_json"]) if r["reasons_json"] else []
                warnings = json.loads(r["warnings_json"]) if r["warnings_json"] else []
            except Exception:
                pass
                
            sig = Signal(
                signal_id=r["signal_id"],
                symbol=r["symbol"],
                timeframe=r["timeframe"],
                candle_close_time=r["candle_close_time"],
                decision_state=r["decision_state"],
                direction=r["direction"],
                alignment_type=r["alignment_type"],
                entry=r["entry"],
                sl=r["sl"],
                tp1=r["tp1"],
                tp2=r["tp2"],
                rr_tp1=r["rr_tp1"],
                rr_tp2=r["rr_tp2"],
                confluence_score=r["confluence_score"],
                directional_score=r["directional_score"],
                quality_score=r["quality_score"],
                market_bias=r["market_bias"],
                setup_direction=r["setup_direction"],
                trigger_direction=r["trigger_direction"],
                execution_direction=r["execution_direction"],
                smc_support_source=r["smc_support_source"],
                smc_resistance_source=r["smc_resistance_source"],
                data_quality_valid=r["data_quality_valid"],
                is_actionable=r["is_actionable"],
                reasons=reasons,
                warnings=warnings,
                outcome_status=r["outcome_status"],
                outcome_time=r["outcome_time"],
                bars_to_outcome=r["bars_to_outcome"],
                realized_r_multiple=r["realized_r_multiple"],
                created_at=r["created_at"],
                primary_regime=_get_row_val(r, "primary_regime", "UNKNOWN"),
                regime_flags=_get_row_val(r, "regime_flags", ""),
                regime_score=_get_row_val(r, "regime_score", 0.0),
                volume_confirmation=_get_row_val(r, "volume_confirmation", "NEUTRAL"),
                vwap_alignment=_get_row_val(r, "vwap_alignment", "NEUTRAL"),
                bos_present=_get_row_val(r, "bos_present", 0),
                choch_present=_get_row_val(r, "choch_present", 0),
                fvg_present=_get_row_val(r, "fvg_present", 0),
                liquidity_sweep_present=_get_row_val(r, "liquidity_sweep_present", 0)
            )
            signals_list.append(sig)
    except Exception as e:
        logger.error(f"Error loading paginated signals: {str(e)}")
    finally:
        conn.close()
    return signals_list

def load_alerts_paginated(limit: int, offset: int, db_path: str = None) -> List[AlertLog]:
    """
    Loads page-limited alerts history.
    """
    conn = get_db_connection(db_path)
    logs = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log ORDER BY sent_at DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        for r in rows:
            logs.append(AlertLog(
                id=r["id"],
                signal_id=r["signal_id"],
                provider=r["provider"],
                status=r["status"],
                sent_at=r["sent_at"],
                error_message=r["error_message"]
            ))
    except Exception as e:
        logger.error(f"Error loading paginated alerts: {str(e)}")
    finally:
        conn.close()
    return logs

def update_signal_outcome(
    signal_id: str,
    outcome_status: str,
    outcome_time: Optional[str],
    bars_to_outcome: Optional[int],
    realized_r: float,
    db_path: str = None
) -> bool:
    """
    Updates the outcome status of a saved signal.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                UPDATE signals 
                SET outcome_status = ?, outcome_time = ?, bars_to_outcome = ?, realized_r_multiple = ?
                WHERE signal_id = ?
            """, (outcome_status, outcome_time, bars_to_outcome, realized_r, signal_id))
        return True
    except Exception as e:
        logger.error(f"Error updating outcome for signal {signal_id}: {str(e)}")
        return False
    finally:
        conn.close()

def insert_alert_log(
    signal_id: str,
    provider: str,
    status: str,
    error_message: Optional[str] = None,
    db_path: str = None
) -> bool:
    """
    Logs an alert action into the alert_log table.
    """
    conn = get_db_connection(db_path)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO alert_log (signal_id, provider, status, sent_at, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (signal_id, provider, status, now_str, error_message))
            inserted = cursor.rowcount > 0
        return inserted
    except Exception as e:
        logger.error(f"Error inserting alert log: {str(e)}")
        return False
    finally:
        conn.close()

def check_alert_exists(signal_id: str, provider: str, db_path: str = None) -> bool:
    """
    Checks if an alert for the given signal_id and provider has already been dispatched.
    """
    conn = get_db_connection(db_path)
    exists = False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM alert_log WHERE signal_id = ? AND provider = ?
        """, (signal_id, provider))
        exists = cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking alert log: {str(e)}")
    finally:
        conn.close()
    return exists

def load_alert_logs(db_path: str = None) -> List[AlertLog]:
    """
    Loads all alert logs.
    """
    conn = get_db_connection(db_path)
    logs = []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log ORDER BY sent_at DESC")
        rows = cursor.fetchall()
        for r in rows:
            logs.append(AlertLog(
                id=r["id"],
                signal_id=r["signal_id"],
                provider=r["provider"],
                status=r["status"],
                sent_at=r["sent_at"],
                error_message=r["error_message"]
            ))
    except Exception as e:
        logger.error(f"Error loading alert logs: {str(e)}")
    finally:
        conn.close()
    return logs

# CSV Export Helpers
def export_signals_to_csv(db_path: str = None) -> str:
    """
    Exports all saved signals to CSV format.
    """
    conn = get_db_connection(db_path)
    output = io.StringIO()
    writer = csv.writer(output)
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY candle_close_time DESC")
        rows = cursor.fetchall()
        
        # Write Header
        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(list(row))
    except Exception as e:
        logger.error(f"Error exporting signals to CSV: {str(e)}")
    finally:
        conn.close()
        
    return output.getvalue()

def export_alert_log_to_csv(db_path: str = None) -> str:
    """
    Exports alert log to CSV format.
    """
    conn = get_db_connection(db_path)
    output = io.StringIO()
    writer = csv.writer(output)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log ORDER BY sent_at DESC")
        rows = cursor.fetchall()
        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(list(row))
    except Exception as e:
        logger.error(f"Error exporting alert log to CSV: {str(e)}")
    finally:
        conn.close()
    return output.getvalue()

def export_trades_to_csv(db_path: str = None) -> str:
    """
    Exports trades to CSV format.
    """
    conn = get_db_connection(db_path)
    output = io.StringIO()
    writer = csv.writer(output)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY opened_at DESC")
        rows = cursor.fetchall()
        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(list(row))
    except Exception as e:
        logger.error(f"Error exporting trades to CSV: {str(e)}")
    finally:
        conn.close()
    return output.getvalue()

# Safe Truncate Helpers
def clear_backtest_results(db_path: str = None):
    """
    Safely clears only backtest_runs and backtest_results.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM backtest_runs;")
            conn.execute("DELETE FROM backtest_results;")
    except Exception as e:
        logger.error(f"Error clearing backtest data: {str(e)}")
    finally:
        conn.close()

def clear_demo_trades(db_path: str = None):
    """
    Safely clears only simulated demo trade entries.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM trades;")
    except Exception as e:
        logger.error(f"Error clearing trades data: {str(e)}")
    finally:
        conn.close()

def clear_alert_log(db_path: str = None):
    """
    Safely clears only alert dispatcher logs.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM alert_log;")
    except Exception as e:
        logger.error(f"Error clearing alert logs: {str(e)}")
    finally:
        conn.close()

def clear_all_journal_data(db_path: str = None):
    """
    Wipes all tables clean.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM signals;")
            conn.execute("DELETE FROM alert_log;")
            conn.execute("DELETE FROM trades;")
            conn.execute("DELETE FROM backtest_runs;")
            conn.execute("DELETE FROM backtest_results;")
    except Exception as e:
        logger.error(f"Error wiping database data: {str(e)}")
    finally:
        conn.close()
