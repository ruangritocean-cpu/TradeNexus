import pytest
from tradenexus.optimization.walk_forward import split_walk_forward_windows

def test_walk_forward_no_lookahead_chronological():
    windows = split_walk_forward_windows(
        total_bars=1000,
        train_window_bars=300,
        test_window_bars=100,
        step_bars=100
    )
    
    for w in windows:
        # Train start must be before train end
        assert w["train_start_idx"] < w["train_end_idx"]
        # Train end must match test start (no gap or overlap)
        assert w["train_end_idx"] == w["test_start_idx"]
        # Test start must be before test end
        assert w["test_start_idx"] < w["test_end_idx"]
        # Absolute lookahead check: test data is strictly after train data
        assert w["train_end_idx"] <= w["test_start_idx"]
