import pytest
from tradenexus.explain.invalidation import generate_invalidation_conditions

def test_invalidation_buy():
    data = {
        "direction": "BUY",
        "entry": 100.0,
        "sl": 95.0,
        "support_level": 92.0,
        "portfolio_risk_status": "OK"
    }
    
    conds = generate_invalidation_conditions(data)
    assert len(conds) == 3
    assert conds[0].condition == "Stop Loss Breach"
    assert conds[0].price_level == 95.0
    assert conds[1].condition == "Swing Support Failure"
    assert conds[1].price_level == 92.0
    assert conds[2].condition == "Market Regime Shift"

def test_invalidation_sell_blocked():
    data = {
        "direction": "SELL",
        "entry": 100.0,
        "sl": 105.0,
        "resistance_level": 108.0,
        "portfolio_risk_status": "BLOCKED"
    }
    
    conds = generate_invalidation_conditions(data)
    assert len(conds) == 4
    assert conds[0].condition == "Stop Loss Breach"
    assert conds[0].price_level == 105.0
    assert conds[1].condition == "Swing Resistance Failure"
    assert conds[1].price_level == 108.0
    assert conds[3].condition == "Portfolio Risk Block"
