import time
import logging
from contextlib import contextmanager
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """
    Context manager to profile specific steps in the scanning/calculation pipeline.
    """
    def __init__(self):
        self.durations: Dict[str, float] = {}
        
    @contextmanager
    def measure(self, step_name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            t1 = time.perf_counter()
            self.durations[step_name] = t1 - t0
            
    def get_summary(self) -> Dict[str, Any]:
        slowest_step = "None"
        slowest_time = 0.0
        warnings = []
        
        for step, val in self.durations.items():
            if val > slowest_time:
                slowest_time = val
                slowest_step = step
                
            # If any step takes more than 10 seconds, trigger warning
            if val > 10.0:
                warnings.append(f"Step '{step}' is running slow: {val:.2f} seconds.")
                
        return {
            "total_duration_seconds": sum(self.durations.values()),
            "durations": self.durations,
            "slowest_step": slowest_step,
            "slowest_time": slowest_time,
            "performance_warnings": warnings
        }
