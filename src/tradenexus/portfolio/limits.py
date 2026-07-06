import logging
from typing import List
from tradenexus.portfolio.risk_models import PortfolioSettings, ExposureSummary, CorrelationRiskResult, RiskLimitResult

logger = logging.getLogger(__name__)

def check_portfolio_risk_limits(
    settings: PortfolioSettings,
    exposure: ExposureSummary,
    correlation: CorrelationRiskResult,
    candidate_direction: str = ""
) -> RiskLimitResult:
    """
    Checks all configured portfolio-level risk limits against current exposure.
    """
    reasons = []
    warnings = []
    blocked_actions = []
    status = "OK"
    
    equity = settings.account_equity
    
    # 1. Daily Realized Loss Limit Check
    max_daily_loss = equity * (settings.max_daily_risk_pct / 100.0)
    # realized_daily_risk is negative for net loss, positive for profit
    # So if it is a net loss (negative) and the absolute value exceeds budget:
    if exposure.realized_daily_risk < 0 and abs(exposure.realized_daily_risk) >= max_daily_loss:
        status = "BLOCKED"
        msg = f"Daily realized loss (${abs(exposure.realized_daily_risk):,.2f}) has breached daily risk limit (${max_daily_loss:,.2f})."
        reasons.append(msg)
        blocked_actions.append("DISPATCH_ALERTS")
        
    # 2. Total Open Risk Limit Check
    max_open_risk = equity * (settings.max_total_open_risk_pct / 100.0)
    if exposure.total_open_risk >= max_open_risk:
        status = "BLOCKED"
        msg = f"Total open risk (${exposure.total_open_risk:,.2f}) has breached maximum open risk limit (${max_open_risk:,.2f})."
        reasons.append(msg)
        blocked_actions.append("DISPATCH_ALERTS")
        
    # 3. Max Concurrent Trades Check
    if exposure.number_of_active_trades >= settings.max_concurrent_trades:
        status = "BLOCKED"
        msg = f"Number of active trades ({exposure.number_of_active_trades}) has reached max concurrent trades limit ({settings.max_concurrent_trades})."
        reasons.append(msg)
        blocked_actions.append("DISPATCH_ALERTS")
        
    # 4. Same Direction Trades Check (only when candidate trade direction is provided)
    if candidate_direction:
        # Check active trades in this specific direction
        # exposure.risk_by_direction keeps track of totals or counts. But since we need counts:
        # we stored same_direction_trade_count which is the maximum of BUY/SELL counts
        # Let's check candidate specific count if we can query it, or check same_direction_trade_count:
        if exposure.same_direction_trade_count >= settings.max_same_direction_trades:
            status = "BLOCKED"
            msg = f"Max same direction trades limit ({settings.max_same_direction_trades}) reached."
            reasons.append(msg)
            blocked_actions.append("DISPATCH_ALERTS")
            
    # 5. Correlation warnings
    if correlation.highly_correlated_pairs:
        warnings.append(correlation.correlation_warning)
        if status == "OK":
            status = "WARNING"
            
    # Check if there's any warning-level thresholds (e.g. open risk nearing 80% of limit)
    if exposure.total_open_risk > 0 and exposure.total_open_risk >= (max_open_risk * 0.8) and status == "OK":
        status = "WARNING"
        warnings.append(f"Total open risk (${exposure.total_open_risk:,.2f}) is nearing maximum allowed limit (${max_open_risk:,.2f}).")
        
    return RiskLimitResult(
        risk_status=status,
        reasons=reasons,
        warnings=warnings,
        blocked_actions=blocked_actions
    )
