import pytest
from tradenexus.optimization.walk_forward import split_walk_forward_windows

def test_walk_forward_splitter_calculation():
    # 500 total bars, train=200, test=50, step=50
    windows = split_walk_forward_windows(
        total_bars=500,
        train_window_bars=200,
        test_window_bars=50,
        step_bars=50
    )
    
    # Window index 0: train [0, 200), test [200, 250)
    # Window index 1: train [50, 250), test [250, 300)
    # Window index 2: train [100, 300), test [300, 350)
    # Window index 3: train [150, 350), test [350, 400)
    # Window index 4: train [200, 400), test [400, 450)
    # Window index 5: train [250, 450), test [450, 500)
    # Window index 6: test_end = 300 * 50 + 200 + 50 = 550 > 500 -> breaks
    assert len(windows) == 6
    assert windows[0]["train_start_idx"] == 0
    assert windows[0]["test_end_idx"] == 250
    assert windows[5]["train_start_idx"] == 250
    assert windows[5]["test_end_idx"] == 500
