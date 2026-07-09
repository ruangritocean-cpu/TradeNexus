import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.presets.preset_library import get_builtin_presets
from tradenexus.presets.preset_apply import generate_preset_diff, apply_preset
from tradenexus.playbook.playbook_models import Playbook
from tradenexus.playbook.playbook_repository import get_active_playbook
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings

TEST_DB = "data/test_apply_diff.sqlite"

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

def test_apply_diff_preview_and_non_mutation():
    preset = get_builtin_presets()[0] # Conservative Trend Follower
    
    # 1. Load defaults
    playbook = get_active_playbook(TEST_DB, "test_ws")
    portfolio = load_portfolio_settings(TEST_DB, "test_ws")
    watchlist = []
    
    # Force default playbook to differ
    playbook.min_confluence_score = 50.0
    
    diff = generate_preset_diff(preset, playbook, portfolio, watchlist)
    
    # 2. Check diff preview values
    assert diff["playbook"]["min_confluence_score"]["current"] == 50.0
    assert diff["playbook"]["min_confluence_score"]["preset"] == preset.min_confluence_score
    assert diff["playbook"]["min_confluence_score"]["will_change"] is True
    
    # Verify no changes are made prior to confirmation/applying
    pb_before = get_active_playbook(TEST_DB, "test_ws")
    assert pb_before.min_confluence_score != preset.min_confluence_score
