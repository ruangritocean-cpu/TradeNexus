import pytest
from tradenexus.optimization.robustness import calculate_robustness_score

def test_robustness_score_calculations():
    # 1. Optimal OOS performance (expectancy >= 0.5, PF >= 2.0, win_rate >= 50%)
    is_metrics = {"expectancy": 0.5, "profit_factor": 2.0, "max_drawdown": 1.0}
    oos_metrics = {"expectancy": 0.5, "profit_factor": 2.0, "win_rate": 50.0, "max_drawdown": 1.0}
    
    score, status = calculate_robustness_score(is_metrics, oos_metrics, parameter_stability=100.0, total_oos_trades=20)
    assert score == 100.0
    assert status == "RECOMMENDED"
    
    # 2. Test degradation penalty (IS expectancy = 1.5, OOS expectancy = 0.3)
    is_metrics_deg = {"expectancy": 1.5, "profit_factor": 2.5, "max_drawdown": 1.0}
    oos_metrics_deg = {"expectancy": 0.3, "profit_factor": 1.2, "win_rate": 40.0, "max_drawdown": 1.0}
    score_deg, status_deg = calculate_robustness_score(is_metrics_deg, oos_metrics_deg, parameter_stability=100.0, total_oos_trades=20)
    
    # Degradation ratio: (1.5 - 0.3) / 1.5 = 1.2 / 1.5 = 80%. Penalty = 30.0 * 80% = 24.0.
    # Score should be significantly lower than 100
    assert score_deg < 80.0
