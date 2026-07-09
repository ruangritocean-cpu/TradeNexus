import pytest
from tradenexus.optimization.parameter_grid import generate_parameter_grid

def test_parameter_grid_generation():
    ranges = {
        "confluence_threshold": [70.0, 75.0],
        "rr_threshold": [1.5, 2.0],
        "adx_threshold": [25.0]
    }
    
    combos, meta = generate_parameter_grid(ranges, max_combinations=10)
    assert len(combos) == 4
    assert meta["grid_total_combinations"] == 4
    assert meta["grid_evaluated_combinations"] == 4
    assert meta["grid_sampling_method"] == "BRUTE_FORCE"
    
    # Check default fallback keys exist
    for c in combos:
        assert "confluence_threshold" in c
        assert "squeeze_block_enabled" in c
        assert c["squeeze_block_enabled"] is True  # Default
