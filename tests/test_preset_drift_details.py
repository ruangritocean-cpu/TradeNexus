import pytest
import os
import json
from tradenexus.journal.db import init_db
from tradenexus.reports.compliance_engine import generate_compliance_report
from tradenexus.playbook.playbook_models import Playbook
from tradenexus.playbook.playbook_repository import save_playbook
from tradenexus.presets.preset_library import get_builtin_presets

TEST_DB = "data/test_preset_drift_details.sqlite"

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

def test_drift_detection_details():
    preset = get_builtin_presets()[0] # Conservative Trend Follower, min_confluence_score = 75.0, min_rr = 2.0
    
    # Save playbook with active preset set but mismatched values
    pb = Playbook(
        playbook_id="default_playbook",
        name="Default Playbook",
        active_preset_id=preset.preset_id,
        min_confluence_score=80.0, # Differ from preset
        min_rr=1.5,                # Differ from preset
        workspace_id="default_workspace"
    )
    save_playbook(pb, TEST_DB, "default_workspace")
    
    report = generate_compliance_report(
        workspace_id="default_workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        db_path=TEST_DB
    )
    
    details = json.loads(report.details_json)
    assert details.get("preset_drift_detected") is True
    
    drift_fields = json.loads(details.get("preset_drift_fields_json", "[]"))
    assert len(drift_fields) >= 2
    
    # Check specific fields
    conf_drift = next((f for f in drift_fields if f["field_name"] == "min_confluence_score"), None)
    assert conf_drift is not None
    assert conf_drift["preset_value"] == 75.0
    assert conf_drift["current_value"] == 80.0
    
    rr_drift = next((f for f in drift_fields if f["field_name"] == "min_rr"), None)
    assert rr_drift is not None
    assert rr_drift["preset_value"] == 2.0
    assert rr_drift["current_value"] == 1.5
