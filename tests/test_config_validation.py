import pytest
import os
from tradenexus.config.validation import validate_system_config

def test_config_validation_checks():
    # 1. Missing data directory warning
    res = validate_system_config(
        data_dir="data/new_verify_dir",
        watchlist_path="data/new_verify_dir/watchlist.json",
        db_path="data/new_verify_dir/db.sqlite",
        scan_interval_seconds=30,
        max_symbols_per_scan=10
    )
    
    assert res["config_status"] == "WARNING"
    assert any("did not exist and was created" in w for w in res["warnings"])
    
    # Cleanup directory
    if os.path.exists("data/new_verify_dir"):
        os.rmdir("data/new_verify_dir")

def test_config_validation_aggressive_and_placeholder():
    res = validate_system_config(
        data_dir="data",
        watchlist_path="data/watchlist.json",
        db_path="data/db.sqlite",
        discord_webhook="https://discord.com/api/webhooks/PLACEHOLDER_KEY",
        tg_token="XYZ_INSERT_HERE",
        scan_interval_seconds=5,  # aggressive
        max_symbols_per_scan=10
    )
    
    assert res["config_status"] == "FAILED"
    assert any("placeholder" in e for e in res["errors"])
    assert any("aggressive" in w for w in res["warnings"])
