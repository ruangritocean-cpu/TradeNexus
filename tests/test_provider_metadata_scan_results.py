import pytest
import datetime
import os
from tradenexus.journal.db import init_db
from tradenexus.scanner.scan_models import ScanResult
from tradenexus.scanner.scan_repository import insert_scan_result, load_scan_results_for_run

TEST_DB = "data/test_scan_provider_metadata.sqlite"

@pytest.fixture
def temp_db():
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError:
            pass
    init_db(TEST_DB)
    yield TEST_DB
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except OSError:
            pass

def test_provider_metadata_save_load(temp_db):
    result = ScanResult(
        scan_run_id="run_prov_test_99",
        signal_id="sig_prov_test_99",
        symbol="BTC-USD",
        timeframe="1h",
        scan_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        provider_used="healthy_mock",
        fallback_used=1,
        data_quality_warnings_json='["warmup"]',
        data_quality_errors_json='[]',
        latest_candle_time="2026-07-09T00:00:00Z",
        bars_available=150
    )
    
    ok = insert_scan_result(result, temp_db)
    assert ok is True
    
    loaded = load_scan_results_for_run("run_prov_test_99", temp_db)
    assert len(loaded) == 1
    assert loaded[0].provider_used == "healthy_mock"
    assert loaded[0].fallback_used == 1
    assert loaded[0].data_quality_status == "VALID"
    assert "warmup" in loaded[0].data_quality_warnings_json
    assert loaded[0].latest_candle_time == "2026-07-09T00:00:00Z"
    assert loaded[0].bars_available == 150
