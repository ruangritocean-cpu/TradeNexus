import pytest
from tradenexus.optimization.parameter_grid import generate_parameter_grid

def test_parameter_grid_safety_truncation():
    ranges = {
        "confluence_threshold": [70.0, 75.0, 80.0],
        "rr_threshold": [1.5, 2.0, 2.5],
        "adx_threshold": [20.0, 25.0]
    } # 3 * 3 * 2 = 18 combinations
    
    # Force max_combinations = 5
    combos, meta = generate_parameter_grid(ranges, max_combinations=5, sampling_seed=123)
    assert len(combos) == 5
    assert meta["grid_total_combinations"] == 18
    assert meta["grid_evaluated_combinations"] == 5
    assert meta["grid_sampling_method"] == "DETERMINISTIC_SAMPLE"
