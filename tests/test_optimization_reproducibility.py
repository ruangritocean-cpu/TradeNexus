import pytest
from tradenexus.optimization.parameter_grid import generate_parameter_grid

def test_reproducibility_sampling_grid():
    ranges = {
        "confluence_threshold": [70.0, 75.0, 80.0],
        "rr_threshold": [1.5, 2.0, 2.5],
        "adx_threshold": [20.0, 25.0]
    } # 18 combinations
    
    # 1. Run with seed 42
    combos_1, meta_1 = generate_parameter_grid(ranges, max_combinations=5, sampling_seed=42)
    # 2. Run again with same seed 42
    combos_2, meta_2 = generate_parameter_grid(ranges, max_combinations=5, sampling_seed=42)
    # 3. Run with different seed 99
    combos_3, meta_3 = generate_parameter_grid(ranges, max_combinations=5, sampling_seed=99)
    
    # Same seed must yield identical combinations
    assert combos_1 == combos_2
    
    # Different seed can yield different combinations
    assert combos_1 != combos_3
