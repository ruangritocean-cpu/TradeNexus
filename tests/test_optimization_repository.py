import os
import pytest
from tradenexus.journal.db import init_db
from tradenexus.optimization.optimization_repository import (
    save_optimization_run,
    update_optimization_run_status,
    save_optimization_result,
    save_parameter_recommendation,
    load_optimization_runs,
    load_optimization_results,
    load_parameter_recommendations
)

TEST_DB = "data/test_opt_repo.sqlite"

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

def test_optimization_repository_crud():
    # 1. Save Run
    save_optimization_run(
        run_id="run_test_123",
        symbol="BTC",
        timeframe="1h",
        start_date="2026-01-01",
        end_date="2026-07-09",
        train_window_bars=200,
        test_window_bars=50,
        step_bars=50,
        max_combinations=50,
        status="RUNNING",
        config_dict={"test": True},
        sampling_seed=42,
        sampling_method="BRUTE_FORCE",
        total_combinations=100,
        evaluated_combinations=50,
        db_path=TEST_DB
    )
    
    runs = load_optimization_runs(limit=5, db_path=TEST_DB)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run_test_123"
    assert runs[0]["status"] == "RUNNING"
    
    # 2. Update Run Status
    update_optimization_run_status("run_test_123", "COMPLETED", db_path=TEST_DB)
    runs_updated = load_optimization_runs(limit=5, db_path=TEST_DB)
    assert runs_updated[0]["status"] == "COMPLETED"
    
    # 3. Save Window Result
    save_optimization_result(
        run_id="run_test_123",
        window_index=0,
        train_start="2026-01-01",
        train_end="2026-03-01",
        test_start="2026-03-01",
        test_end="2026-04-01",
        params_dict={"confluence_threshold": 75.0},
        in_sample_metrics={"expectancy": 0.4},
        out_sample_metrics={"expectancy": 0.2},
        robustness_score=85.0,
        warnings=[],
        db_path=TEST_DB
    )
    
    res = load_optimization_results("run_test_123", db_path=TEST_DB)
    assert len(res) == 1
    assert res[0]["window_index"] == 0
    assert res[0]["robustness_score"] == 85.0
    
    # 4. Save parameter recommendation
    save_parameter_recommendation(
        recommendation_id="rec_test_123",
        symbol="BTC",
        timeframe="1h",
        params_dict={"confluence_threshold": 75.0},
        robustness_score=85.0,
        sample_size=12,
        recommendation_status="RECOMMENDED",
        valid_from="2026-07-09T00:00:00",
        notes="High quality recommendation",
        db_path=TEST_DB
    )
    
    recs = load_parameter_recommendations("BTC", "1h", db_path=TEST_DB)
    assert len(recs) == 1
    assert recs[0]["recommendation_id"] == "rec_test_123"
    assert recs[0]["recommendation_status"] == "RECOMMENDED"
