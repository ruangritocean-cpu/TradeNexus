import pytest
from tradenexus.explain.brief_models import DecisionBrief, BriefRiskPlan, BriefPortfolioCheck
from tradenexus.explain.templates import (
    format_compact_brief,
    format_full_brief,
    format_alert_brief,
    format_scan_card_brief
)

def test_template_formatters():
    brief = DecisionBrief(
        symbol="BTC-USD",
        timeframe="1h",
        decision_state="ENTRY TRIGGERED",
        direction="BUY",
        alignment_type="TREND_FOLLOWING",
        confluence_score=85.0,
        primary_regime="TRENDING_UP",
        regime_flags=["HIGH_VOLATILITY"],
        risk_plan=BriefRiskPlan(entry=100.0, sl=90.0, tp1=120.0, tp2=140.0, rr_tp1=2.0, position_size=10.0, risk_amount=100.0),
        portfolio_check=BriefPortfolioCheck(portfolio_risk_status="OK", reasons=[], warnings=[]),
        invalidation_conditions=[],
        headline="Bullish Trigger",
        summary="Bullish CDC trend confirmed",
        reasons=["CDC actionzone green", "MACD cross"],
        warnings=["Low liquidity"],
        next_action="Execute entry",
        created_at="2026-07-06"
    )
    
    # 1. Compact format check
    compact_text = format_compact_brief(brief)
    lines = compact_text.split("\n")
    assert len(lines) == 5
    assert "Asset: BTC-USD" in lines[0]
    assert "Direction: BUY" in lines[1]
    
    # 2. Alert format check
    alert_text = format_alert_brief(brief)
    assert "TradeNexus Alert" in alert_text
    assert "BTC-USD" in alert_text
    
    # 3. Scan card format check
    scan_text = format_scan_card_brief(brief)
    assert "Confluence: 85%" in scan_text
    assert "RR: 2.00R" in scan_text
    assert "Bullish CDC trend confirmed" in scan_text
