import os
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def validate_system_config(
    data_dir: str,
    watchlist_path: str,
    db_path: str,
    discord_webhook: str = "",
    tg_token: str = "",
    scan_interval_seconds: int = 30,
    max_symbols_per_scan: int = 15
) -> Dict[str, Any]:
    """
    Validates global paths, secret patterns, and scanner parameters.
    """
    errors = []
    warnings = []
    
    # 1. Directory Checks
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir, exist_ok=True)
            warnings.append(f"Data directory '{data_dir}' did not exist and was created.")
        except Exception as e:
            errors.append(f"Failed to create data directory '{data_dir}': {str(e)}")
            
    # 2. SQLite Write Check
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    try:
        # Check write access to DB folder
        test_file = os.path.join(db_dir or ".", "write_test.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        errors.append(f"Database directory is not writable: {str(e)}")
        
    # 3. Secret Exposure Checks
    # Discord Webhook pattern validation: check if it doesn't look like a placeholder or raw key in code
    placeholder_patterns = [
        r"INSERT_HERE", r"YOUR_WEBHOOK", r"TODO", r"PLACEHOLDER", r"XYZ"
    ]
    
    if discord_webhook:
        for pat in placeholder_patterns:
            if re.search(pat, discord_webhook, re.IGNORECASE):
                errors.append("Discord webhook contains a default placeholder string.")
                
    if tg_token:
        for pat in placeholder_patterns:
            if re.search(pat, tg_token, re.IGNORECASE):
                errors.append("Telegram bot token contains a default placeholder string.")
                
    # 4. Scanner aggressiveness check
    if scan_interval_seconds < 10:
        warnings.append(f"Scan interval ({scan_interval_seconds}s) is aggressive. Recommend >= 10s to prevent API locks.")
        
    if max_symbols_per_scan > 50:
        warnings.append(f"Max symbols per scan ({max_symbols_per_scan}) is high. May trigger Yahoo Finance blocks.")
        
    status = "FAILED" if errors else ("WARNING" if warnings else "OK")
    return {
        "config_status": status,
        "errors": errors,
        "warnings": warnings
    }
