import pytest
from tradenexus.optimization.walk_forward import split_walk_forward_windows

def test_final_holdout_isolation():
    # 500 total bars, train=200, test=50, step=50, holdout=100
    # Optimization boundary: 500 - 100 = 400 bars
    windows = split_walk_forward_windows(
        total_bars=500,
        train_window_bars=200,
        test_window_bars=50,
        step_bars=50,
        final_holdout_bars=100
    )
    
    # Max test_end must be <= 400
    for w in windows:
        assert w["test_end_idx"] <= 400
        
    assert len(windows) == 4  # Window index 3 test_end = 150 + 200 + 50 = 400.
