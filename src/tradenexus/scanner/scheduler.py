import datetime
import logging
import threading
from typing import Dict, Any, Optional
from tradenexus.scanner.scan_engine import run_watchlist_scan

logger = logging.getLogger(__name__)

# Module-level thread-safe globals
_scheduler_lock = threading.Lock()
_state = "IDLE"
_last_scan_started_at: Optional[str] = None
_last_scan_finished_at: Optional[str] = None
_last_scan_run_id: Optional[str] = None
_last_error: Optional[str] = None

def get_scheduler_status() -> Dict[str, Any]:
    """
    Returns the current runtime status of the scheduler.
    """
    with _scheduler_lock:
        return {
            "scheduler_state": _state,
            "last_scan_started_at": _last_scan_started_at,
            "last_scan_finished_at": _last_scan_finished_at,
            "last_scan_run_id": _last_scan_run_id,
            "last_error": _last_error
        }

def trigger_scheduled_scan(
    db_path: str = None,
    watchlist_path: str = None,
    discord_webhook: str = "",
    tg_bot_token: str = "",
    tg_chat_id: str = "",
    max_symbols: int = 20,
    min_seconds_between_scans: int = 30,
    force_all_candles: bool = False
) -> Dict[str, Any]:
    """
    Triggers a sequential watchlist scan, enforcing overlap and rate-limit controls.
    """
    global _state, _last_scan_started_at, _last_scan_finished_at, _last_scan_run_id, _last_error
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    with _scheduler_lock:
        # 1. Check overlap
        if _state == "RUNNING":
            logger.warning("Scan trigger skipped: another scan is already running.")
            return {
                "status": "SKIPPED_OVERLAP",
                "scheduler_state": _state,
                "last_scan_run_id": _last_scan_run_id
            }
            
        # 2. Check rate-limit guard
        if _last_scan_finished_at:
            try:
                last_fin = datetime.datetime.fromisoformat(_last_scan_finished_at)
                elapsed = (now - last_fin).total_seconds()
                if elapsed < min_seconds_between_scans:
                    msg = f"Scan rate-limited. Must wait {min_seconds_between_scans - elapsed:.1f} seconds."
                    logger.warning(msg)
                    return {
                        "status": "FAILED",
                        "error_message": msg,
                        "scheduler_state": _state
                    }
            except Exception:
                pass
                
        # 3. Transition to RUNNING
        _state = "RUNNING"
        _last_scan_started_at = now.isoformat()
        _last_error = None
        
    # Execute scan outside lock to prevent blocking status reads
    try:
        res = run_watchlist_scan(
            db_path=db_path,
            watchlist_path=watchlist_path,
            discord_webhook=discord_webhook,
            tg_bot_token=tg_bot_token,
            tg_chat_id=tg_chat_id,
            max_symbols=max_symbols,
            force_all_candles=force_all_candles
        )
        
        with _scheduler_lock:
            _state = "COMPLETED"
            _last_scan_finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _last_scan_run_id = res["scan_run_id"]
            return {
                "status": "COMPLETED",
                "scan_run_id": res["scan_run_id"],
                "scheduler_state": _state
            }
            
    except Exception as ex:
        err_msg = str(ex)
        with _scheduler_lock:
            _state = "FAILED"
            _last_scan_finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _last_error = err_msg
            logger.error(f"Scheduled scan failed: {err_msg}")
            return {
                "status": "FAILED",
                "error_message": err_msg,
                "scheduler_state": _state
            }

def reset_scheduler_state():
    """
    Resets the scheduler state to IDLE (primarily for testing purposes).
    """
    global _state, _last_scan_started_at, _last_scan_finished_at, _last_scan_run_id, _last_error
    with _scheduler_lock:
        _state = "IDLE"
        _last_scan_started_at = None
        _last_scan_finished_at = None
        _last_scan_run_id = None
        _last_error = None
