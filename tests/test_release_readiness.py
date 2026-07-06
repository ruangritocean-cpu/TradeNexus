import pytest
import os
from tradenexus.journal.db import init_db
from tradenexus.diagnostics.report import generate_release_readiness_report

TEST_DB = "data/test_diagnostics_report.sqlite"

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

def test_release_readiness_report_blocked():
    # If a critical path or database is invalid -> BLOCKED
    res = generate_release_readiness_report(
        db_path="invalid_path/db.sqlite",
        watchlist_path=None
    )
    assert res["release_status"] == "BLOCKED"
    assert len(res["errors"]) > 0

def test_release_readiness_report_ready():
    res = generate_release_readiness_report(
        db_path=TEST_DB,
        watchlist_path="data/watchlist.json",
        discord_webhook="https://discord.com/api/webhooks/mock",
        tg_token="123:mock"
    )
    # Correctly configured returns READY or WARNING depending on watchlist exists checks
    assert res["release_status"] in ["READY", "WARNING"]
