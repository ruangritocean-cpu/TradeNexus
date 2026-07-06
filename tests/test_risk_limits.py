import pytest
from tradenexus.portfolio.risk_models import PortfolioSettings, ExposureSummary, CorrelationRiskResult
from tradenexus.portfolio.limits import check_portfolio_risk_limits

def test_risk_limits_ok():
    settings = PortfolioSettings(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        max_daily_risk_pct=3.0,
        max_total_open_risk_pct=5.0,
        max_concurrent_trades=5
    )
    
    exposure = ExposureSummary(
        realized_daily_risk=0.0, # no loss today
        total_open_risk=2000.0,  # $2000 open risk (2.0%)
        total_open_risk_pct=2.0,
        potential_setup_risk=0.0,
        potential_setup_risk_pct=0.0,
        number_of_active_trades=2,
        same_direction_trade_count=1,
        pending_actionable_setup_count=0
    )
    
    correlation = CorrelationRiskResult({}, [], [], "")
    
    res = check_portfolio_risk_limits(settings, exposure, correlation)
    assert res.risk_status == "OK"

def test_risk_limits_blocked_by_open_risk():
    settings = PortfolioSettings(
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        max_total_open_risk_pct=5.0
    )
    
    exposure = ExposureSummary(
        realized_daily_risk=0.0,
        total_open_risk=6000.0,  # $6,000 open risk (6.0% > 5.0%)
        total_open_risk_pct=6.0,
        potential_setup_risk=0.0,
        potential_setup_risk_pct=0.0,
        number_of_active_trades=3,
        same_direction_trade_count=2,
        pending_actionable_setup_count=0
    )
    
    correlation = CorrelationRiskResult({}, [], [], "")
    
    res = check_portfolio_risk_limits(settings, exposure, correlation)
    assert res.risk_status == "BLOCKED"
    assert "open risk limit" in res.reasons[0]

def test_risk_limits_blocked_by_daily_loss():
    settings = PortfolioSettings(
        account_equity=100000.0,
        max_daily_risk_pct=3.0
    )
    
    exposure = ExposureSummary(
        realized_daily_risk=-3500.0, # -$3,500 realized loss (3.5% > 3.0%)
        total_open_risk=1000.0,
        total_open_risk_pct=1.0,
        potential_setup_risk=0.0,
        potential_setup_risk_pct=0.0,
        number_of_active_trades=1,
        same_direction_trade_count=1,
        pending_actionable_setup_count=0
    )
    
    correlation = CorrelationRiskResult({}, [], [], "")
    
    res = check_portfolio_risk_limits(settings, exposure, correlation)
    assert res.risk_status == "BLOCKED"
    assert "Daily realized loss" in res.reasons[0]

def test_risk_limits_warning_by_correlation():
    settings = PortfolioSettings(
        account_equity=100000.0,
        max_total_open_risk_pct=5.0
    )
    
    exposure = ExposureSummary(
        realized_daily_risk=0.0,
        total_open_risk=1000.0,
        total_open_risk_pct=1.0,
        potential_setup_risk=0.0,
        potential_setup_risk_pct=0.0,
        number_of_active_trades=1,
        same_direction_trade_count=1,
        pending_actionable_setup_count=0
    )
    
    correlation = CorrelationRiskResult(
        correlation_matrix={},
        highly_correlated_pairs=[("BTC-USD", "ETH-USD", 0.85)],
        same_direction_correlation_warnings=[],
        correlation_warning="High correlation detected"
    )
    
    res = check_portfolio_risk_limits(settings, exposure, correlation)
    assert res.risk_status == "WARNING"
    assert "High correlation detected" in res.warnings[0]
