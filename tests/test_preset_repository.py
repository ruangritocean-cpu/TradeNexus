import pytest
import os
import sqlite3
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord
from tradenexus.presets.preset_repository import (
    load_all_presets, save_preset, delete_preset, duplicate_builtin_preset,
    load_apply_history, log_apply_history, load_preset
)

TEST_DB = "data/test_preset_repo.sqlite"

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

def test_custom_preset_crud():
    # Load all presets initially (should only have 7 builtins seeded)
    presets = load_all_presets("my_ws", TEST_DB)
    assert len(presets) == 7
    
    # Save a custom preset
    custom_p = StrategyPreset(
        preset_id="custom_scalper",
        workspace_id="my_ws",
        name="Custom Scalper",
        description="Desc",
        asset_class="Crypto",
        trading_style="Scalping",
        risk_profile="Aggressive"
    )
    assert save_preset(custom_p, "my_ws", TEST_DB) is True
    
    # Check it exists
    loaded = load_preset("custom_scalper", "my_ws", TEST_DB)
    assert loaded is not None
    assert loaded.name == "Custom Scalper"
    assert loaded.is_builtin == 0
    
    # Delete it
    assert delete_preset("custom_scalper", "my_ws", TEST_DB) is True
    assert load_preset("custom_scalper", "my_ws", TEST_DB) is None
    
def test_cannot_save_or_delete_builtin_presets():
    # Builtin preset_id "conservative_trend_follower"
    builtin = load_preset("conservative_trend_follower", "my_ws", TEST_DB)
    assert builtin is not None
    assert builtin.is_builtin == 1
    
    # Try to modify (should fail)
    assert save_preset(builtin, "__builtin__", TEST_DB) is False
    # Try to delete (should fail)
    assert delete_preset("conservative_trend_follower", "__builtin__", TEST_DB) is False
