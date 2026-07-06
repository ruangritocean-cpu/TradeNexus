import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.portfolio.portfolio_repository import save_portfolio_settings
from tradenexus.portfolio.risk_models import PortfolioSettings
from tradenexus.explain.decision_brief import generate_decision_brief

TEST_DB = "data/test_db_brief.sqlite"

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass

def test_decision_brief_generation_entry_triggered():
    settings = PortfolioSettings(account_equity=100000.0, risk_per_trade_pct=1.0)
    save_portfolio_settings(settings, TEST_DB)
    
    data = {
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "decision_state": "ENTRY TRIGGERED",
        "direction": "BUY",
        "alignment_type": "TREND_FOLLOWING",
        "confluence_score": 85.0,
        "primary_regime": "TRENDING_UP",
        "regime_flags": ["HIGH_VOLATILITY"],
        "entry": 100.0,
        "sl": 90.0,
        "tp1": 120.0,
        "tp2": 140.0,
        "rr_tp1": 2.0,
        "warnings": ["Low liquidity warning"]
    }
    
    brief = generate_decision_brief(data, db_path=TEST_DB)
    
    assert brief.symbol == "BTC-USD"
    assert brief.decision_state == "ENTRY TRIGGERED"
    assert brief.direction == "BUY"
    assert brief.risk_plan is not None
    assert brief.risk_plan.position_size == 100.0  # $1,000 risk / $10 risk per unit = 100 units
    assert "EXECUTE TRIGGERED ENTRY" in brief.next_action
    assert any("Trend hierarchy is aligned" in r for r in brief.reasons)
    assert any("Stop Loss Breach" in c.condition for c in brief.invalidation_conditions)

def test_decision_brief_blocked_by_portfolio():
    # Set max open risk to 0% to force BLOCKED status
    settings = PortfolioSettings(account_equity=100000.0, max_total_open_risk_pct=0.0)
    save_portfolio_settings(settings, TEST_DB)
    
    data = {
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "decision_state": "ENTRY TRIGGERED",
        "direction": "BUY",
        "alignment_type": "TREND_FOLLOWING",
        "confluence_score": 85.0,
        "primary_regime": "TRENDING_UP",
        "entry": 100.0,
        "sl": 90.0,
        "tp1": 120.0,
        "rr_tp1": 2.0,
        "warnings": []
    }
    
    brief = generate_decision_brief(data, db_path=TEST_DB)
    
    # Portfolio status is BLOCKED
    assert brief.portfolio_check.portfolio_risk_status == "BLOCKED"
    # Technical state remains ENTRY TRIGGERED
    assert brief.decision_state == "ENTRY TRIGGERED"
    # Action is blocked
    assert "ALERT BLOCKED" in brief.next_action
    assert any("Portfolio Risk Block" in c.condition for c in brief.invalidation_conditions)
