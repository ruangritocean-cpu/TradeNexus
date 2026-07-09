import pytest
from tradenexus.presets.preset_library import get_builtin_presets

def test_preset_library_load():
    presets = get_builtin_presets()
    assert len(presets) == 7
    
    names = [p.name for p in presets]
    assert "Conservative Trend Follower" in names
    assert "Balanced Swing Trader" in names
    assert "Gold Intraday Scalper" in names
    
    # Assert every builtin has proper builtin tags
    for p in presets:
        assert p.workspace_id == "__builtin__"
        assert p.is_builtin == 1
        assert p.min_rr >= 1.0
        assert p.min_confluence_score > 0.0
