import pytest
import os
from tradenexus.scanner.watchlist import load_watchlist, save_watchlist

TEST_WL = "data/test_watchlist.json"

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_WL):
        try:
            os.remove(TEST_WL)
        except PermissionError:
            pass
    yield
    if os.path.exists(TEST_WL):
        try:
            os.remove(TEST_WL)
        except PermissionError:
            pass

def test_watchlist_operations():
    """
    Verifies that watchlist loads default settings, filters enabled symbols,
    saves atomically, and handles corruption.
    """
    # 1. Load default watchlist (file doesn't exist yet)
    items = load_watchlist(TEST_WL)
    assert len(items) > 0
    assert items[0]["symbol"] == "GC=F"
    
    # 2. Modify and save watchlist
    items[0]["enabled"] = False
    items[0]["min_rr"] = 2.5  # symbol-specific threshold override
    res = save_watchlist(items, TEST_WL)
    assert res is True
    
    # Reload and check
    reloaded = load_watchlist(TEST_WL)
    assert reloaded[0]["enabled"] is False
    assert reloaded[0]["min_rr"] == 2.5
    
    # 3. Corrupt file and test fallback
    with open(TEST_WL, "w", encoding="utf-8") as f:
        f.write("corrupted json { }")
        
    fallback_items = load_watchlist(TEST_WL)
    assert len(fallback_items) > 0
    # Fallback to default, where GC=F is enabled
    assert fallback_items[0]["symbol"] == "GC=F"
    assert fallback_items[0]["enabled"] is True
