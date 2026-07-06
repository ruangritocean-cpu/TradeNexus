import logging
from typing import List

logger = logging.getLogger(__name__)

def summarize_warnings(raw_warnings: List[str]) -> List[str]:
    """
    Summarizes and sorts warnings by severity, putting critical blocks first.
    Deduplicates inputs.
    """
    if not raw_warnings:
        return ["No critical warnings."]
        
    # Deduplicate
    unique_warnings = []
    for w in raw_warnings:
        cleaned = w.strip()
        if cleaned and cleaned not in unique_warnings:
            unique_warnings.append(cleaned)
            
    if not unique_warnings:
        return ["No critical warnings."]
        
    # Priority sorting helper
    def get_priority(w_str: str) -> int:
        w_lower = w_str.lower()
        if "breach" in w_lower or "block" in w_lower or "limit" in w_lower or "invalid" in w_lower or "veto" in w_lower:
            return 0  # High priority (Critical blocks)
        elif "warning" in w_lower or "correlation" in w_lower or "volatility" in w_lower or "liquidity" in w_lower:
            return 1  # Medium priority (Warnings)
        return 2      # Low priority (Info / Notes)
        
    sorted_warnings = sorted(unique_warnings, key=get_priority)
    return sorted_warnings
