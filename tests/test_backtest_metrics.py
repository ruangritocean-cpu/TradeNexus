import pytest
from tradenexus.backtest.metrics import calculate_backtest_metrics

def test_metrics_calculation_standard():
    """
    Verifies that the backtest performance metrics (win_rate, profit_factor, expectancy, dd)
    are calculated accurately under standard simulated outcomes.
    """
    trades = [
        {"status": "TP1_HIT", "realized_r_multiple": 1.5, "bars_to_outcome": 10},
        {"status": "SL_HIT", "realized_r_multiple": -1.0, "bars_to_outcome": 5},
        {"status": "TP2_HIT", "realized_r_multiple": 2.0, "bars_to_outcome": 15},
        {"status": "SL_HIT", "realized_r_multiple": -1.0, "bars_to_outcome": 4},
        {"status": "EXPIRED", "realized_r_multiple": 0.5, "bars_to_outcome": 20}
    ]
    
    metrics = calculate_backtest_metrics(trades)
    
    assert metrics["total_signals"] == 5
    assert metrics["total_trades"] == 5
    
    # Wins: TP1_HIT (+1.5), TP2_HIT (+2.0), EXPIRED (+0.5) -> 3 wins. Win rate: 3/5 = 60%
    assert metrics["win_rate"] == 60.0
    
    # Expectancy (Average R): (1.5 - 1.0 + 2.0 - 1.0 + 0.5) / 5 = 2.0 / 5 = 0.4
    assert metrics["expectancy"] == 0.4
    
    # Gross Wins: 1.5 + 2.0 + 0.5 = 4.0. Gross Losses: 1.0 + 1.0 = 2.0. Profit Factor: 4.0 / 2.0 = 2.0
    assert metrics["profit_factor"] == 2.0
    
    # Max consecutive losses: 1
    assert metrics["max_consecutive_losses"] == 1
    
    # Average holding bars: (10 + 5 + 15 + 4 + 20) / 5 = 54 / 5 = 10.8
    assert metrics["average_holding_bars"] == 10.8

def test_metrics_no_losses():
    """
    Verifies that a dataset with zero losses (perfect win rate) does not crash the system.
    """
    trades = [
        {"status": "TP1_HIT", "realized_r_multiple": 1.5, "bars_to_outcome": 5},
        {"status": "TP2_HIT", "realized_r_multiple": 2.0, "bars_to_outcome": 8}
    ]
    
    metrics = calculate_backtest_metrics(trades)
    assert metrics["win_rate"] == 100.0
    assert metrics["profit_factor"] == float('inf')
