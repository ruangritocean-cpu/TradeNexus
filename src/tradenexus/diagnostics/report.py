import datetime
import logging
from typing import Dict, Any, List
from tradenexus.diagnostics.health import check_system_health
from tradenexus.diagnostics.db_integrity import check_database_integrity
from tradenexus.config.validation import validate_system_config

logger = logging.getLogger(__name__)

def generate_release_readiness_report(
    db_path: str = None,
    watchlist_path: str = None,
    data_dir: str = "data",
    discord_webhook: str = "",
    tg_token: str = "",
    symbols: List[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates diagnostics and builds a release readiness summary.
    """
    if symbols is None:
        symbols = []
        
    health = check_system_health(db_path, watchlist_path, discord_webhook, tg_token)
    db_integrity = check_database_integrity(db_path)
    
    config_validation = validate_system_config(
        data_dir=data_dir,
        watchlist_path=watchlist_path or "data/watchlist.json",
        db_path=db_path or "data/tradenexus_journal.sqlite",
        discord_webhook=discord_webhook,
        tg_token=tg_token
    )
    
    errors = []
    warnings = []
    
    errors.extend(health["errors"])
    errors.extend(db_integrity["errors"])
    errors.extend(config_validation["errors"])
    
    warnings.extend(health["warnings"])
    warnings.extend(db_integrity["warnings"])
    warnings.extend(config_validation["warnings"])
    
    # Calculate status
    if errors:
        release_status = "BLOCKED"
    elif warnings:
        release_status = "WARNING"
    else:
        release_status = "READY"
        
    return {
        "release_status": release_status,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "health_checks": health,
        "db_integrity": db_integrity,
        "config_validation": config_validation,
        "errors": errors,
        "warnings": warnings
    }
