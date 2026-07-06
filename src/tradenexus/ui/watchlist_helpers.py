import json
import logging

logger = logging.getLogger(__name__)

def sort_top_actionable_setups(scan_results: list) -> list:
    """
    Filters out NO TRADE and WATCH decisions, and sorts remaining setups by:
    1. confluence_score desc
    2. rr_tp1 desc
    """
    valid_states = ["ENTRY TRIGGERED", "READY"]
    filtered = []
    for r in scan_results:
        state = r.get("decision_state") if isinstance(r, dict) else getattr(r, "decision_state", "")
        if state in valid_states:
            filtered.append(r)
            
    def get_val(item, key):
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, 0.0)
        
    filtered.sort(key=lambda x: (get_val(x, "confluence_score") or 0.0, get_val(x, "rr_tp1") or 0.0), reverse=True)
    return filtered

def count_warnings_in_results(scan_results: list) -> int:
    """
    Returns the total number of warnings across all results.
    """
    total = 0
    for r in scan_results:
        warnings_str = r.get("warnings_json", "[]") if isinstance(r, dict) else getattr(r, "warnings_json", "[]")
        try:
            warnings = json.loads(warnings_str) if isinstance(warnings_str, str) else warnings_str
            if isinstance(warnings, list):
                total += len(warnings)
        except Exception:
            pass
    return total
