import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_repository import (
    load_builtin_presets, load_all_presets, save_preset, delete_preset, load_preset
)

TEST_DB = "data/test_builtin_scope.sqlite"

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

def test_builtin_presets_scope_rules():
    # 1. Built-in presets use workspace_id "__builtin__"
    builtins = load_builtin_presets(TEST_DB)
    assert len(builtins) == 7
    for b in builtins:
        assert b.workspace_id == "__builtin__"
        assert b.is_builtin == 1
        
    # 2. Built-in presets appear in every workspace query
    ws_1 = load_all_presets("workspace_1", TEST_DB)
    ws_2 = load_all_presets("workspace_2", TEST_DB)
    assert len(ws_1) == 7
    assert len(ws_2) == 7
    
    # 3. Built-in presets cannot be edited or deleted
    sample = builtins[0]
    sample.name = "Mutated Name"
    # Try save_preset to __builtin__ workspace
    assert save_preset(sample, "__builtin__", TEST_DB) is False
    # Try save_preset to another workspace (but since is_builtin = 1, it must be blocked)
    assert save_preset(sample, "workspace_1", TEST_DB) is False
    
    # Verify DB still has original values
    original = load_preset(sample.preset_id, "workspace_1", TEST_DB)
    assert original.name != "Mutated Name"
    
    # Try delete
    assert delete_preset(sample.preset_id, "__builtin__", TEST_DB) is False
    assert delete_preset(sample.preset_id, "workspace_1", TEST_DB) is False
