import pytest
import os
import shutil
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_library import get_builtin_presets
from tradenexus.presets.preset_apply import apply_preset
from tradenexus.scanner.watchlist import load_watchlist, save_watchlist

TEST_DB = "data/test_preset_wl_safety.sqlite"

@pytest.fixture(autouse=True)
def setup_teardown():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    ws_dir = os.path.join("data", "workspaces")
    if os.path.exists(ws_dir):
        try:
            shutil.rmtree(ws_dir)
        except Exception:
            pass
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    if os.path.exists(ws_dir):
        try:
            shutil.rmtree(ws_dir)
        except Exception:
            pass

def test_watchlist_suggestions_append_safety():
    # Setup initial watchlist
    initial_wl = [
        {"symbol": "GC=F", "display_name": "Gold", "asset_class": "Commodities", "enabled": False, "min_rr": 3.0}
    ]
    assert save_watchlist(initial_wl, workspace_id="test_ws") is True
    
    preset = get_builtin_presets()[0] # Conservative Trend Follower, suggests ["GC=F", "^GSPC", "EURUSD=X"]
    
    # Apply preset with watchlist enabled
    apply_preset(
        preset=preset,
        workspace_id="test_ws",
        apply_playbook=False,
        apply_portfolio=False,
        apply_watchlist=True,
        db_path=TEST_DB
    )
    
    reloaded = load_watchlist(workspace_id="test_ws")
    
    # 1. Existing GC=F should still be present, and NOT overwritten (enabled should remain False, min_rr 3.0)
    gc_item = next((item for item in reloaded if item["symbol"] == "GC=F"), None)
    assert gc_item is not None
    assert gc_item["enabled"] is False
    assert gc_item["min_rr"] == 3.0
    
    # 2. Suggested missing symbols should be appended
    symbols = {item["symbol"] for item in reloaded}
    assert "^GSPC" in symbols
    assert "EURUSD=X" in symbols
    assert len(reloaded) == 3 # original 1 + new 2
