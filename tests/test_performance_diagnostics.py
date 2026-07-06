import pytest
import time
from tradenexus.diagnostics.performance import PerformanceTracker

def test_performance_tracker():
    tracker = PerformanceTracker()
    
    with tracker.measure("fetch_data"):
        time.sleep(0.05)
        
    with tracker.measure("calculations"):
        time.sleep(0.02)
        
    summary = tracker.get_summary()
    
    assert summary["total_duration_seconds"] >= 0.07
    assert summary["slowest_step"] == "fetch_data"
    assert summary["durations"]["fetch_data"] >= 0.04
    assert summary["durations"]["calculations"] >= 0.01
