import pytest
import os
import datetime
from tradenexus.journal.db import init_db
from tradenexus.scanner.scan_models import ScanRun, ScanResult
from tradenexus.scanner.scan_repository import (
    insert_scan_run, 
    insert_scan_result, 
    load_scan_runs, 
    load_scan_results_for_run,
    load_scan_results_paginated
)

TEST_DB = "data/test_scan_repo.sqlite"

@pytest.fixture(autouse=True)
def setup_test_db():
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

def test_scan_repository_operations():
    """
    Verifies that scan runs and results can be logged, retrieved with UTC timestamps,
    and paginate correctly.
    """
    # 1. Create mock run
    run_id = "test_run_123"
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    run = ScanRun(
        scan_run_id=run_id,
        started_at=now_utc,
        finished_at=now_utc,
        status="COMPLETED",
        total_symbols=2,
        success_count=2,
        warning_count=0,
        error_count=0,
        skipped_count=0,
        config_json="{}"
    )
    
    res1 = insert_scan_run(run, TEST_DB)
    assert res1 is True
    
    # 2. Insert mock scan results
    result_a = ScanResult(
        scan_run_id=run_id,
        signal_id="sig_abc_123",
        symbol="BTC-USD",
        timeframe="1h",
        scan_time=now_utc,
        symbol_status="SUCCESS",
        decision_state="ENTRY TRIGGERED",
        direction="BUY",
        alignment_type="TREND_FOLLOWING",
        confluence_score=85.0,
        rr_tp1=2.0,
        primary_regime="TRENDING_UP",
        regime_flags_json="[]",
        data_quality_status="VALID",
        alert_status="SENT",
        journal_status="SAVED",
        reasons_json="[]",
        warnings_json="[]",
        error_message="",
        created_at=now_utc
    )
    
    res2 = insert_scan_result(result_a, TEST_DB)
    assert res2 is True
    
    # 3. Load from DB
    loaded_runs = load_scan_runs(limit=10, offset=0, db_path=TEST_DB)
    assert len(loaded_runs) == 1
    assert loaded_runs[0].scan_run_id == run_id
    assert loaded_runs[0].started_at == now_utc
    
    loaded_results = load_scan_results_for_run(run_id, TEST_DB)
    assert len(loaded_results) == 1
    assert loaded_results[0].symbol == "BTC-USD"
    assert loaded_results[0].signal_id == "sig_abc_123"
    
    # 4. Pagination check
    paginated_results = load_scan_results_paginated(limit=5, offset=0, db_path=TEST_DB)
    assert len(paginated_results) == 1
