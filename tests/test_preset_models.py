import pytest
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord

def test_preset_models_instantiation():
    preset = StrategyPreset(
        preset_id="test_preset",
        workspace_id="test_ws",
        name="Test Preset",
        description="Test Desc",
        asset_class="Forex",
        trading_style="Swing",
        risk_profile="Conservative"
    )
    assert preset.preset_id == "test_preset"
    assert preset.is_builtin == 0
    assert preset.min_rr == 1.5
    
    record = PresetApplyRecord(
        apply_id="apply_1",
        preset_id="test_preset",
        workspace_id="test_ws",
        applied_at="now",
        applied_sections=["playbook"],
        previous_values="{}",
        new_values="{}",
        warnings=[]
    )
    assert record.apply_id == "apply_1"
    assert "playbook" in record.applied_sections
