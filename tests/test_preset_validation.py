import pytest
from tradenexus.presets.preset_models import StrategyPreset
from tradenexus.presets.preset_validation import validate_preset

def test_preset_validation_rules():
    # Valid preset
    p = StrategyPreset(
        preset_id="v_preset",
        workspace_id="test_ws",
        name="Valid Preset",
        description="Desc",
        asset_class="Indices",
        trading_style="Trend",
        risk_profile="Conservative",
        min_confluence_score=70.0,
        min_rr=1.5,
        allowed_sessions=["LONDON", "NEWYORK"],
        default_portfolio_risk_pct=1.0
    )
    is_ok, errs, warns = validate_preset(p)
    assert is_ok is True
    assert len(errs) == 0
    
    # Invalid confluence score (> 100)
    p.min_confluence_score = 150.0
    is_ok, errs, warns = validate_preset(p)
    assert is_ok is False
    assert any("Confluence threshold" in e for e in errs)
    
    # Invalid min_rr (< 1.0)
    p.min_confluence_score = 70.0
    p.min_rr = 0.5
    is_ok, errs, warns = validate_preset(p)
    assert is_ok is False
    assert any("Minimum Risk-to-Reward Ratio" in e for e in errs)
    
    # Invalid session name
    p.min_rr = 1.5
    p.allowed_sessions = ["TOKYO"]
    is_ok, errs, warns = validate_preset(p)
    assert is_ok is False
    assert any("Session" in e for e in errs)
    
    # Invalid risk percentage (> 5.0)
    p.allowed_sessions = ["LONDON"]
    p.default_portfolio_risk_pct = 6.5
    is_ok, errs, warns = validate_preset(p)
    assert is_ok is False
    assert any("Default portfolio risk" in e for e in errs)
