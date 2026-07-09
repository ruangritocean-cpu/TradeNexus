import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord
from tradenexus.presets.preset_repository import save_preset, load_preset, load_apply_history, log_apply_history

TEST_DB = "data/test_preset_isolation.sqlite"

@pytest.fixture(autouse=True)
def setup_teardown():
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

def test_preset_workspace_isolation():
    # Save custom preset in Workspace A
    preset_a = StrategyPreset(
        preset_id="scalper_x",
        workspace_id="workspace_a",
        name="Scalper A",
        description="Desc",
        asset_class="Crypto",
        trading_style="Scalping",
        risk_profile="Aggressive"
    )
    assert save_preset(preset_a, "workspace_a", TEST_DB) is True
    
    # Save custom preset in Workspace B with same preset_id
    preset_b = StrategyPreset(
        preset_id="scalper_x",
        workspace_id="workspace_b",
        name="Scalper B",
        description="Desc",
        asset_class="Crypto",
        trading_style="Scalping",
        risk_profile="Moderate"
    )
    assert save_preset(preset_b, "workspace_b", TEST_DB) is True
    
    # Verify isolation
    loaded_a = load_preset("scalper_x", "workspace_a", TEST_DB)
    assert loaded_a.name == "Scalper A"
    assert loaded_a.risk_profile == "Aggressive"
    
    loaded_b = load_preset("scalper_x", "workspace_b", TEST_DB)
    assert loaded_b.name == "Scalper B"
    assert loaded_b.risk_profile == "Moderate"
    
    # Log apply history in workspace A
    rec_a = PresetApplyRecord(
        apply_id="apply_a",
        preset_id="scalper_x",
        workspace_id="workspace_a",
        applied_at="2026-07-09T00:00:00Z",
        applied_sections=["playbook"],
        previous_values="{}",
        new_values="{}",
        warnings=[]
    )
    assert log_apply_history(rec_a, TEST_DB) is True
    
    # Log apply history in workspace B
    rec_b = PresetApplyRecord(
        apply_id="apply_b",
        preset_id="scalper_x",
        workspace_id="workspace_b",
        applied_at="2026-07-09T01:00:00Z",
        applied_sections=["playbook"],
        previous_values="{}",
        new_values="{}",
        warnings=[]
    )
    assert log_apply_history(rec_b, TEST_DB) is True
    
    # Verify history logs isolation
    history_a = load_apply_history("workspace_a", TEST_DB)
    assert len(history_a) == 1
    assert history_a[0].apply_id == "apply_a"
    
    history_b = load_apply_history("workspace_b", TEST_DB)
    assert len(history_b) == 1
    assert history_b[0].apply_id == "apply_b"
