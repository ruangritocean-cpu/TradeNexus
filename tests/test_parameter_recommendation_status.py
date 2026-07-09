import pytest
from tradenexus.optimization.robustness import calculate_robustness_score

def test_recommendation_status_evaluation():
    # 1. Reject insufficient data if setups < 5
    is_metrics = {"expectancy": 0.5, "profit_factor": 1.8}
    oos_metrics = {"expectancy": 0.4, "profit_factor": 1.6, "win_rate": 55.0, "max_drawdown": 1.0}
    
    score, status = calculate_robustness_score(is_metrics, oos_metrics, parameter_stability=100.0, total_oos_trades=3)
    assert status == "REJECTED_INSUFFICIENT_DATA"
    
    # 2. Reject poor performance if negative expectancy
    oos_poor = {"expectancy": -0.1, "profit_factor": 0.8, "win_rate": 30.0, "max_drawdown": 2.0}
    score_poor, status_poor = calculate_robustness_score(is_metrics, oos_poor, parameter_stability=100.0, total_oos_trades=20)
    assert status_poor == "REJECTED_POOR_OOS"
    
    # 3. Warning low sample if setups >= 5 and < 15
    score_warn, status_warn = calculate_robustness_score(is_metrics, oos_metrics, parameter_stability=100.0, total_oos_trades=8)
    assert status_warn == "WARNING_LOW_SAMPLE"
