import pytest
import os
import shutil
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_library import get_builtin_presets
from tradenexus.presets.preset_apply import apply_preset
from tradenexus.presets.preset_repository import load_apply_history
from tradenexus.playbook.playbook_repository import get_active_playbook
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings

TEST_DB = "data/test_preset_apply.sqlite"

@pytest.fixture(autouse=True)
def setup_teardown():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
    # Clean watchlist workspace directory
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

def test_preset_apply_flow():
    preset = get_builtin_presets()[0] # Conservative Trend Follower
    
    # 1. Apply Playbook Only (default behavior)
    res = apply_preset(
        preset=preset,
        workspace_id="test_ws",
        apply_playbook=True,
        apply_portfolio=False,
        apply_watchlist=False,
        db_path=TEST_DB
    )
    
    assert "playbook" in res["applied_sections"]
    assert "portfolio" not in res["applied_sections"]
    
    # Verify playbook values updated
    pb = get_active_playbook(TEST_DB, "test_ws")
    assert pb.min_confluence_score == preset.min_confluence_score
    assert pb.min_rr == preset.min_rr
    assert pb.active_preset_id == preset.preset_id
    
    # Verify portfolio was NOT changed
    port = load_portfolio_settings(TEST_DB, "test_ws")
    assert port.risk_per_trade_pct == 1.0 # Default value, unchanged
    
    # 2. Apply both Playbook and Portfolio
    res2 = apply_preset(
        preset=preset,
        workspace_id="test_ws",
        apply_playbook=True,
        apply_portfolio=True,
        apply_watchlist=False,
        db_path=TEST_DB
    )
    
    assert "playbook" in res2["applied_sections"]
    assert "portfolio" in res2["applied_sections"]
    
    port2 = load_portfolio_settings(TEST_DB, "test_ws")
    assert port2.risk_per_trade_pct == preset.default_portfolio_risk_pct
    
    # Verify apply history was logged
    history = load_apply_history("test_ws", TEST_DB)
    assert len(history) == 2
    assert history[0].preset_id == preset.preset_id
