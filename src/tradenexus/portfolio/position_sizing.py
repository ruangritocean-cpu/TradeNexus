import logging
import math
from tradenexus.portfolio.risk_models import PositionSizeResult

logger = logging.getLogger(__name__)

def calculate_position_size(
    account_equity: float,
    risk_per_trade_pct: float,
    entry: float,
    stop_loss: float,
    direction: str,
    point_value: float = 1.0,
    contract_multiplier: float = 1.0,
    commission_pct: float = 0.0,
    slippage_points: float = 0.0,
    min_position_size: float = 0.01,
    position_step: float = 0.01,
    tp1: float = 0.0,
    tp2: float = 0.0
) -> PositionSizeResult:
    """
    Calculates position size taking stop loss, commissions, slippage, and stepping limits into account.
    """
    # 1. Validation checks
    if entry <= 0 or stop_loss <= 0:
        return PositionSizeResult(
            risk_amount=0.0, risk_points=0.0, position_size_units=0.0,
            estimated_loss_at_sl=0.0, estimated_profit_tp1=0.0, estimated_profit_tp2=0.0,
            r_multiple_tp1=0.0, r_multiple_tp2=0.0,
            sizing_status="ERROR", sizing_warning="Invalid entry or stop loss price values."
        )
        
    is_buy = "BUY" in direction.upper()
    is_sell = "SELL" in direction.upper()
    
    if not is_buy and not is_sell:
        return PositionSizeResult(
            risk_amount=0.0, risk_points=0.0, position_size_units=0.0,
            estimated_loss_at_sl=0.0, estimated_profit_tp1=0.0, estimated_profit_tp2=0.0,
            r_multiple_tp1=0.0, r_multiple_tp2=0.0,
            sizing_status="ERROR", sizing_warning="Direction must be BUY or SELL."
        )
        
    if is_buy and stop_loss >= entry:
        return PositionSizeResult(
            risk_amount=0.0, risk_points=0.0, position_size_units=0.0,
            estimated_loss_at_sl=0.0, estimated_profit_tp1=0.0, estimated_profit_tp2=0.0,
            r_multiple_tp1=0.0, r_multiple_tp2=0.0,
            sizing_status="ERROR", sizing_warning="BUY requires stop loss to be below entry price."
        )
        
    if is_sell and stop_loss <= entry:
        return PositionSizeResult(
            risk_amount=0.0, risk_points=0.0, position_size_units=0.0,
            estimated_loss_at_sl=0.0, estimated_profit_tp1=0.0, estimated_profit_tp2=0.0,
            r_multiple_tp1=0.0, r_multiple_tp2=0.0,
            sizing_status="ERROR", sizing_warning="SELL requires stop loss to be above entry price."
        )
        
    # 2. Risk points and risk amount
    risk_points = abs(entry - stop_loss)
    risk_amount = account_equity * (risk_per_trade_pct / 100.0)
    
    # 3. Incorporate slippage and commission costs into unit risk
    # Slippage increases distance by 2x slippage points (slipping entry and slipping SL)
    points_risk = risk_points + (2.0 * slippage_points)
    
    # Dollar cost of commissions (round-trip) per unit
    commission_cost_per_unit = (entry + stop_loss) * (commission_pct / 100.0)
    
    # Dollar risk per unit
    unit_risk_usd = (points_risk * contract_multiplier * point_value) + commission_cost_per_unit
    
    if unit_risk_usd <= 0:
        return PositionSizeResult(
            risk_amount=risk_amount, risk_points=risk_points, position_size_units=0.0,
            estimated_loss_at_sl=0.0, estimated_profit_tp1=0.0, estimated_profit_tp2=0.0,
            r_multiple_tp1=0.0, r_multiple_tp2=0.0,
            sizing_status="ERROR", sizing_warning="Risk calculation error: unit risk <= 0."
        )
        
    # Calculate initial raw units
    raw_units = risk_amount / unit_risk_usd
    
    # Round to position step
    if position_step > 0:
        stepped_units = round(raw_units / position_step) * position_step
    else:
        stepped_units = raw_units
        
    status = "OK"
    warning = ""
    
    if stepped_units < min_position_size:
        status = "WARNING"
        warning = f"Calculated position size ({stepped_units:.4f}) is below the minimum required ({min_position_size:.4f})."
        stepped_units = 0.0
        
    # Calculate actual loss at stop loss
    estimated_loss = stepped_units * unit_risk_usd
    
    # Check if estimated loss is excessively high
    if estimated_loss > (risk_amount * 1.2):
        status = "WARNING"
        warning = f"Position size yields loss ({estimated_loss:.2f}) exceeding risk budget ({risk_amount:.2f})."
        
    # Est Profit TP1 / TP2
    def est_profit(tp_target):
        if tp_target <= 0:
            return 0.0
        tp_points = abs(tp_target - entry) - (2.0 * slippage_points)
        tp_rev = tp_points * contract_multiplier * point_value
        tp_comm = (entry + tp_target) * (commission_pct / 100.0)
        return stepped_units * (tp_rev - tp_comm)
        
    est_tp1 = est_profit(tp1)
    est_tp2 = est_profit(tp2)
    
    r_tp1 = (est_tp1 / estimated_loss) if estimated_loss > 0 else 0.0
    r_tp2 = (est_tp2 / estimated_loss) if estimated_loss > 0 else 0.0
    
    return PositionSizeResult(
        risk_amount=risk_amount,
        risk_points=risk_points,
        position_size_units=stepped_units,
        estimated_loss_at_sl=estimated_loss,
        estimated_profit_tp1=est_tp1,
        estimated_profit_tp2=est_tp2,
        r_multiple_tp1=r_tp1,
        r_multiple_tp2=r_tp2,
        sizing_status=status,
        sizing_warning=warning
    )
