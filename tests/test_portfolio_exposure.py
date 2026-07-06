import pytest
import os
import datetime
from tradenexus.journal.db import init_db, get_db_connection
from tradenexus.portfolio.risk_models import PortfolioSettings, SymbolRiskProfile
from tradenexus.portfolio.portfolio_repository import save_portfolio_settings, save_symbol_profile
from tradenexus.portfolio.exposure import calculate_portfolio_exposure
from tradenexus.scanner.scan_models import ScanRun, ScanResult
from tradenexus.scanner.scan_repository import insert_scan_run, insert_scan_result

TEST_DB = "data/test_port_exposure.sqlite"

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

def test_portfolio_exposure_calculation():
    """
    Verifies that active trades, setups, and daily outcomes are aggregated,
    grouped, and deduplicated correctly.
    """
    settings = PortfolioSettings(account_equity=100000.0, risk_per_trade_pct=1.0) # $1,000 per trade
    save_portfolio_settings(settings, TEST_DB)
    
    # Save a symbol risk profile
    profile_btc = SymbolRiskProfile(symbol="BTC-USD", asset_class="Crypto", point_value=1.0, contract_multiplier=1.0)
    save_symbol_profile(profile_btc, TEST_DB)
    
    conn = get_db_connection(TEST_DB)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 1. Insert an active trade
    with conn:
        conn.execute(
            """
            INSERT INTO trades (
                trade_id, signal_id, symbol, direction, entry, sl, tp1, tp2, status, opened_at, realized_r_multiple
            ) VALUES ('trade_1', 'sig_1', 'BTC-USD', 'BUY', 100.0, 90.0, 120.0, 140.0, 'OPEN', ?, 0.0)
            """,
            (now_str,)
        )
    conn.close()
    
    # 2. Insert a scan run and result setups (one duplicates sig_1, one is new setup)
    run = ScanRun(
        scan_run_id="run_1", started_at=now_str, finished_at=now_str, status="COMPLETED",
        total_symbols=2, success_count=2, warning_count=0, error_count=0, skipped_count=0, config_json="{}"
    )
    insert_scan_run(run, TEST_DB)
    
    # Duplicate setup BTC-USD (should be skipped by deduplication because trade_1 covers it)
    res_a = ScanResult(
        scan_run_id="run_1", signal_id="sig_1", symbol="BTC-USD", timeframe="1h", scan_time=now_str,
        symbol_status="SUCCESS", decision_state="ENTRY TRIGGERED", direction="BUY", alignment_type="TREND_FOLLOWING",
        confluence_score=80.0, rr_tp1=2.0, primary_regime="TRENDING_UP", regime_flags_json="[]",
        data_quality_status="VALID", alert_status="SENT", journal_status="SAVED", reasons_json="[]",
        warnings_json="[]", error_message="", created_at=now_str
    )
    insert_scan_result(res_a, TEST_DB)
    
    # New setup ETH-USD (should count toward potential risk)
    res_b = ScanResult(
        scan_run_id="run_1", signal_id="sig_2", symbol="ETH-USD", timeframe="1h", scan_time=now_str,
        symbol_status="SUCCESS", decision_state="ENTRY TRIGGERED", direction="BUY", alignment_type="TREND_FOLLOWING",
        confluence_score=80.0, rr_tp1=2.0, primary_regime="TRENDING_UP", regime_flags_json="[]",
        data_quality_status="VALID", alert_status="SENT", journal_status="SAVED", reasons_json="[]",
        warnings_json="[]", error_message="", created_at=now_str
    )
    insert_scan_result(res_b, TEST_DB)
    
    # Calculate exposure
    exp = calculate_portfolio_exposure(TEST_DB, settings)
    
    # Assert active trade counts
    assert exp.number_of_active_trades == 1
    # BTC trade risk: entry 100, sl 90 = 10 points. Risk = $1,000
    assert exp.total_open_risk == 1000.0
    assert exp.total_open_risk_pct == 1.0
    
    # Assert potential setups counts (sig_1 is deduped, sig_2 is new -> 1 setup)
    assert exp.pending_actionable_setup_count == 1
    assert exp.potential_setup_risk == 1000.0  # $1,000
