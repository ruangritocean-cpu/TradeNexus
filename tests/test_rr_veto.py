import pytest
from tradenexus.signals.risk import validate_trade_risk

def test_risk_reward_veto():
    """
    Verifies that the Risk Engine vetoes trades that do not meet the minimum Risk-to-Reward (RR) threshold.
    """
    # 1. Trade that meets the RR requirement
    # Entry: 4157, SL: 4100 (Risk: 57 points), TP1: 4250 (Reward: 93 points) -> RR: 1.63 >= 1.5 (PASS)
    res_pass = validate_trade_risk(
        price=4157.0,
        decision="BUY",
        support=4100.0,
        resistance=4300.0,
        atr=20.0,
        rr_min=1.5
    )
    assert res_pass["Decision"] == "BUY"
    assert not res_pass["Vetoed"]
    
    # 2. Trade that is vetoed because structural resistance blocks TP1
    # Major resistance is at 4200. Entry: 4157, SL: 4100 (Risk: 57).
    # Minimum required TP1 is 4157 + (57 * 1.5) = 4242.5.
    # But since resistance is at 4200, it blocks the trade target.
    res_veto = validate_trade_risk(
        price=4157.0,
        decision="BUY",
        support=4100.0,
        resistance=4200.0, # resistance is too close!
        atr=20.0,
        rr_min=1.5
    )
    assert res_veto["Decision"] == "NO TRADE"
    assert res_veto["Vetoed"]
    assert "RR below minimum threshold" in res_veto["VetoReason"]
