import pytest
from tradenexus.signals.rules import evaluate_mtf_hierarchy

def test_mtf_hierarchy_labeling():
    """
    Verifies that the MTF Hierarchy rules correctly label trade setups
    as TREND_FOLLOWING, COUNTER_TREND_SCALP, or CONFLICTED.
    """
    # 1. Trend following aligned buy
    res_tf = evaluate_mtf_hierarchy("Bullish", "Bullish", "Bullish", "Bullish")
    assert res_tf["alignment_type"] == "TREND_FOLLOWING"
    
    # 2. Counter-trend scalp buy
    res_ct = evaluate_mtf_hierarchy("Bearish", "Bearish", "Bullish", "Bullish")
    assert res_ct["alignment_type"] == "COUNTER_TREND_SCALP"
    
    # 3. Conflicted mixed timeframes
    res_conf = evaluate_mtf_hierarchy("Bullish", "Bearish", "Bullish", "Bearish")
    assert res_conf["alignment_type"] == "CONFLICTED"
