import datetime
from typing import Dict, Any

# In-memory dictionary to store provider health stats
_health_registry: Dict[str, Dict[str, Any]] = {}

def get_provider_health(provider_name: str) -> Dict[str, Any]:
    """
    Returns the health statistics for a given provider.
    Initializes standard values if not tracked yet.
    """
    if provider_name not in _health_registry:
        _health_registry[provider_name] = {
            "provider_name": provider_name,
            "last_success_at": None,
            "last_failure_at": None,
            "failure_count": 0,
            "success_count": 0,
            "total_fetch_duration": 0.0,
            "average_fetch_duration": 0.0,
            "health_status": "OK"
        }
    return _health_registry[provider_name]

def record_success(provider_name: str, duration_seconds: float):
    """
    Logs a successful fetch operation for a provider.
    """
    stats = get_provider_health(provider_name)
    stats["last_success_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stats["success_count"] += 1
    stats["total_fetch_duration"] += duration_seconds
    stats["average_fetch_duration"] = stats["total_fetch_duration"] / (stats["success_count"] + stats["failure_count"])
    
    # Recovery behavior
    if stats["failure_count"] > 0:
        stats["failure_count"] = max(0, stats["failure_count"] - 1)
        
    if stats["failure_count"] == 0:
        stats["health_status"] = "OK"
    elif stats["failure_count"] < 3:
        stats["health_status"] = "WARNING"
    else:
        stats["health_status"] = "FAILED"

def record_failure(provider_name: str):
    """
    Logs a failed fetch operation for a provider.
    """
    stats = get_provider_health(provider_name)
    stats["last_failure_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stats["failure_count"] += 1
    
    # Calculate averages
    total_calls = stats["success_count"] + stats["failure_count"]
    stats["average_fetch_duration"] = stats["total_fetch_duration"] / total_calls if total_calls > 0 else 0.0
    
    if stats["failure_count"] >= 3:
        stats["health_status"] = "FAILED"
    else:
        stats["health_status"] = "WARNING"

def load_all_providers_health() -> Dict[str, Dict[str, Any]]:
    """
    Returns health logs for all tracked providers.
    """
    return _health_registry
