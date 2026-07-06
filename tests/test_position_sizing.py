import pytest
from tradenexus.portfolio.position_sizing import calculate_position_size

def test_position_sizing_buy():
    """
    Test standard BUY position sizing with contract multiplier, point value,
    and step rounding.
    """
    res = calculate_position_size(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,  # $1,000 risk
        entry=100.0,
        stop_loss=90.0,  # 10 points risk
        direction="BUY",
        point_value=1.0,
        contract_multiplier=1.0,
        min_position_size=0.01,
        position_step=0.1,
        tp1=120.0
    )
    
    assert res.sizing_status == "OK"
    assert res.risk_amount == 1000.0
    assert res.risk_points == 10.0
    # $1000 risk / $10 risk per unit = 100 units
    assert res.position_size_units == 100.0
    assert res.estimated_loss_at_sl == 1000.0
    assert res.r_multiple_tp1 == 2.0  # 20 reward / 10 risk

def test_position_sizing_sell():
    res = calculate_position_size(
        account_equity=50000.0,
        risk_per_trade_pct=2.0,  # $1,000 risk
        entry=50.0,
        stop_loss=55.0,  # 5 points risk
        direction="SELL",
        point_value=2.0,  # multiplier point value is 2.0
        contract_multiplier=1.0,
        min_position_size=0.01,
        position_step=1.0,
        tp1=40.0
    )
    assert res.sizing_status == "OK"
    # Unit risk = 5 * 2.0 = 10 USD
    # Units = $1,000 / 10 = 100 units
    assert res.position_size_units == 100.0

def test_position_sizing_invalid_sl():
    # BUY stop loss is equal or higher than entry -> error
    res_buy = calculate_position_size(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        entry=100.0,
        stop_loss=100.0,
        direction="BUY"
    )
    assert res_buy.sizing_status == "ERROR"
    assert "below entry" in res_buy.sizing_warning
    
    # SELL stop loss is equal or lower than entry -> error
    res_sell = calculate_position_size(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        entry=100.0,
        stop_loss=99.0,
        direction="SELL"
    )
    assert res_sell.sizing_status == "ERROR"
    assert "above entry" in res_sell.sizing_warning

def test_position_sizing_costs():
    # Slippage and commission increase the risk, leading to smaller position size
    res_no_costs = calculate_position_size(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        entry=100.0,
        stop_loss=90.0,
        direction="BUY",
        commission_pct=0.0,
        slippage_points=0.0,
        position_step=0.0001
    )
    
    res_with_costs = calculate_position_size(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        entry=100.0,
        stop_loss=90.0,
        direction="BUY",
        commission_pct=0.1,  # 0.1% commission
        slippage_points=0.5, # 0.5 points slippage
        position_step=0.0001
    )
    
    assert res_with_costs.position_size_units < res_no_costs.position_size_units
