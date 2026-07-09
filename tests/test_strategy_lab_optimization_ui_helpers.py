import pytest
from tradenexus.ui.strategy_lab_tab import grid_meta_desc

def test_grid_meta_desc_formatting():
    assert grid_meta_desc(est=100, limit=50) == "sampled from 100"
    assert grid_meta_desc(est=30, limit=50) == "brute force"
