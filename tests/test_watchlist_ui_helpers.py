import pytest
import json
from tradenexus.ui.watchlist_helpers import sort_top_actionable_setups, count_warnings_in_results

def test_watchlist_ui_helpers():
    """
    Verifies that sort_top_actionable_setups properly filters out non-actionable decisions,
    orders by confluence and RR, and count_warnings_in_results aggregates warning count correctly.
    """
    results = [
        {"symbol": "A", "decision_state": "WATCH", "confluence_score": 90.0, "rr_tp1": 2.0, "warnings_json": "[]"},
        {"symbol": "B", "decision_state": "ENTRY TRIGGERED", "confluence_score": 75.0, "rr_tp1": 1.8, "warnings_json": '["Warn1"]'},
        {"symbol": "C", "decision_state": "READY", "confluence_score": 85.0, "rr_tp1": 1.5, "warnings_json": '["Warn2", "Warn3"]'},
        {"symbol": "D", "decision_state": "NO TRADE", "confluence_score": 95.0, "rr_tp1": 3.0, "warnings_json": "[]"},
        {"symbol": "E", "decision_state": "ENTRY TRIGGERED", "confluence_score": 85.0, "rr_tp1": 2.2, "warnings_json": "[]"}
    ]
    
    # 1. Test sort and filter
    sorted_setups = sort_top_actionable_setups(results)
    assert len(sorted_setups) == 3
    # Ordered by:
    # 1st: Symbol E (confluence = 85.0, RR = 2.2)
    # 2nd: Symbol C (confluence = 85.0, RR = 1.5)
    # 3rd: Symbol B (confluence = 75.0, RR = 1.8)
    assert sorted_setups[0]["symbol"] == "E"
    assert sorted_setups[1]["symbol"] == "C"
    assert sorted_setups[2]["symbol"] == "B"
    
    # 2. Test warning counts
    warns = count_warnings_in_results(results)
    assert warns == 3  # Symbol B (1) + Symbol C (2)
