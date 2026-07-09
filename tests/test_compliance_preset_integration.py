import pytest
import os
import json
from tradenexus.journal.db import init_db
from tradenexus.reports.compliance_engine import generate_compliance_report
from tradenexus.playbook.playbook_models import Playbook
from tradenexus.playbook.playbook_repository import save_playbook

TEST_DB = "data/test_compliance_preset.sqlite"

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

def test_compliance_preset_metadata():
    # Save playbook with active preset set to 'conservative_trend_follower'
    pb = Playbook(
        playbook_id="default_playbook",
        name="Default Playbook",
        active_preset_id="conservative_trend_follower",
        workspace_id="default_workspace"
    )
    save_playbook(pb, TEST_DB, "default_workspace")
    
    report = generate_compliance_report(
        workspace_id="default_workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    
    # Verify metadata fields are embedded in details_json
    details = json.loads(report.details_json)
    assert details.get("active_preset_id") == "conservative_trend_follower"
    assert details.get("active_preset_name") == "Conservative Trend Follower"
    assert "preset_drift_detected" in details
