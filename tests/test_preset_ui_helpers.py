import pytest
from tradenexus.presets.preset_library import get_builtin_presets

def test_preset_comparison_formatting():
    presets = get_builtin_presets()
    matrix = []
    for p in presets:
        matrix.append({
            "Name": p.name,
            "Style": p.trading_style,
            "Risk": f"{p.default_portfolio_risk_pct}%"
        })
    assert len(matrix) == 7
    assert matrix[0]["Name"] == "Conservative Trend Follower"
    assert "Trend Following" in [m["Style"] for m in matrix]
