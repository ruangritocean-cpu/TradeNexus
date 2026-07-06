import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.diagnostics.health import check_system_health

TEST_DB = "data/test_diagnostics_health.sqlite"

@pytest.fixture(autouse=True)
def setup_db():
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

def test_system_health_ok():
    res = check_system_health(
        db_path=TEST_DB,
        watchlist_path="data/watchlist.json",
        discord_webhook="https://discord.com/api/webhooks/mock",
        tg_bot_token="123456:mock"
    )
    
    assert res["health_status"] in ["OK", "WARNING"]
    assert res["checks"]["database_connection"] == "OK"
    assert res["checks"]["journal_read_write"] == "OK"

def test_system_health_missing_secrets():
    res = check_system_health(
        db_path=TEST_DB,
        watchlist_path="data/watchlist.json",
        discord_webhook=None,
        tg_bot_token=None
    )
    
    # Missing optional keys results in WARNING, not crash
    assert res["health_status"] == "WARNING"
    assert res["checks"]["discord_configured"] == "WARNING"
    assert res["checks"]["telegram_configured"] == "WARNING"
    assert len(res["warnings"]) > 0

def test_system_health_db_failed():
    # Pass an invalid directory as DB path to force failure
    res = check_system_health(
        db_path="invalid_dir/non_existent.sqlite",
        watchlist_path=None
    )
    
    assert res["health_status"] == "FAILED"
    assert res["checks"]["database_connection"] == "FAILED"
    assert len(res["errors"]) > 0
