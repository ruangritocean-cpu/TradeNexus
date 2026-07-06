import json
import os
import tempfile
import logging
import copy
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST_PATH = os.path.join("data", "watchlist.json")

DEFAULT_ITEMS = [
    {"symbol": "GC=F", "display_name": "Gold Future", "asset_class": "Commodities", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "SI=F", "display_name": "Silver Future", "asset_class": "Commodities", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "CL=F", "display_name": "Crude Oil", "asset_class": "Commodities", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "NQ=F", "display_name": "Nasdaq 100", "asset_class": "Indices", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "ES=F", "display_name": "S&P 500", "asset_class": "Indices", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "YM=F", "display_name": "Dow 30", "asset_class": "Indices", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "BTC-USD", "display_name": "Bitcoin", "asset_class": "Crypto", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""},
    {"symbol": "ETH-USD", "display_name": "Ethereum", "asset_class": "Crypto", "enabled": True, "preferred_timeframes": ["1h", "4h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True, "alert_ready_enabled": False, "alert_entry_enabled": True, "notes": ""}
]

def validate_watchlist_schema(items: List[Dict[str, Any]]) -> bool:
    """
    Validates that the watchlist has the correct format and required fields.
    """
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        if "symbol" not in item:
            return False
    return True

def load_watchlist(path: str = None) -> List[Dict[str, Any]]:
    """
    Loads watchlist from watchlist.json.
    Auto-creates file with defaults if missing.
    Falls back to defaults if corrupted.
    """
    if path is None:
        path = DEFAULT_WATCHLIST_PATH
        
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_watchlist(copy.deepcopy(DEFAULT_ITEMS), path)
        return copy.deepcopy(DEFAULT_ITEMS)
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if validate_watchlist_schema(data):
            # Enforce missing keys are initialized
            for item in data:
                if "alert_ready_enabled" not in item:
                    item["alert_ready_enabled"] = False
                if "alert_entry_enabled" not in item:
                    item["alert_entry_enabled"] = True
            return data
        else:
            logger.warning(f"Watchlist file {path} has invalid schema. Falling back to defaults.")
            return copy.deepcopy(DEFAULT_ITEMS)
    except Exception as e:
        logger.warning(f"Failed to load watchlist file {path}: {str(e)}. Falling back to defaults.")
        return copy.deepcopy(DEFAULT_ITEMS)

def save_watchlist(items: List[Dict[str, Any]], path: str = None) -> bool:
    """
    Saves watchlist to path atomically.
    Writes to temporary file first and replaces atomically to avoid corruption.
    """
    if path is None:
        path = DEFAULT_WATCHLIST_PATH
        
    if not validate_watchlist_schema(items):
        logger.error("Watchlist validation failed. Refusing to save.")
        return False
        
    try:
        dir_name = os.path.dirname(path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        # Create temp file in same directory to ensure atomic replace on the same filesystem
        fd, temp_path = tempfile.mkstemp(dir=dir_name or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=4)
            # Atomic replacement
            if os.path.exists(path):
                os.remove(path)
            os.rename(temp_path, path)
            return True
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
    except Exception as e:
        logger.error(f"Error saving watchlist atomically: {str(e)}")
        return False
