from typing import List, Dict, Any

def split_walk_forward_windows(
    total_bars: int,
    train_window_bars: int,
    test_window_bars: int,
    step_bars: int,
    final_holdout_bars: int = 0
) -> List[Dict[str, Any]]:
    """
    Computes train/test indices for sequential walk-forward window slices.
    Also isolates an optional final holdout period at the end of the dataset.
    """
    if total_bars <= 0:
        return []
        
    optimization_bars = total_bars - final_holdout_bars
    if optimization_bars < train_window_bars + test_window_bars:
        return []
        
    windows = []
    window_idx = 0
    
    while True:
        train_start = window_idx * step_bars
        train_end = train_start + train_window_bars
        test_start = train_end
        test_end = test_start + test_window_bars
        
        # Stop building windows when the test slice extends past the optimization boundary
        if test_end > optimization_bars:
            break
            
        windows.append({
            "window_index": window_idx,
            "train_start_idx": train_start,
            "train_end_idx": train_end,
            "test_start_idx": test_start,
            "test_end_idx": test_end
        })
        
        window_idx += 1
        
    return windows
