import pytest
import os
import shutil
import sqlite3
from tradenexus.workspace.workspace_repository import load_workspaces, create_workspace, get_workspace, set_workspace_active
from tradenexus.workspace.workspace_context import get_active_workspace_id, set_active_workspace_id
from tradenexus.journal.db import init_db
from tradenexus.journal.repository import insert_signal, load_signals, check_alert_exists, insert_alert_log
from tradenexus.journal.models import Signal
from tradenexus.playbook.playbook_models import Playbook
from tradenexus.playbook.playbook_repository import save_playbook, load_playbooks, get_active_playbook
from tradenexus.portfolio.risk_models import PortfolioSettings
from tradenexus.portfolio.portfolio_repository import save_portfolio_settings, load_portfolio_settings
from tradenexus.scanner.scan_models import ScanRun, ScanResult
from tradenexus.scanner.scan_repository import insert_scan_run, load_scan_runs, insert_scan_result, load_scan_results_paginated
from tradenexus.scanner.watchlist import load_watchlist, save_watchlist

TEST_DB = "data/test_workspace_journal.sqlite"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup clean database
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
            
    # Clean workspace watchlist directory
    ws_dir = os.path.join("data", "workspaces")
    if os.path.exists(ws_dir):
        try:
            shutil.rmtree(ws_dir)
        except Exception:
            pass
            
    init_db(TEST_DB)
    
    # Set default workspace active
    set_active_workspace_id("default_workspace")
    
    yield
    
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except PermissionError:
            pass
            
    if os.path.exists(ws_dir):
        try:
            shutil.rmtree(ws_dir)
        except Exception:
            pass

# Test 1: Workspace creation and context setting
def test_workspace_creation_and_context():
    # Default active workspace is default_workspace
    assert get_active_workspace_id() == "default_workspace"
    
    # Create new workspaces
    assert create_workspace("crypto_trading", "Crypto Trading", "Crypto desk", TEST_DB) is True
    assert create_workspace("futures_trading", "Futures Trading", "Futures desk", TEST_DB) is True
    
    # Verify loaded workspaces list
    workspaces = load_workspaces(TEST_DB)
    ws_ids = [w.workspace_id for w in workspaces]
    assert "default_workspace" in ws_ids
    assert "crypto_trading" in ws_ids
    assert "futures_trading" in ws_ids
    
    # Switch context
    set_active_workspace_id("crypto_trading")
    assert get_active_workspace_id() == "crypto_trading"

# Test 2: Signals isolation across workspaces
def test_signals_isolation():
    sig = Signal(
        signal_id="sig_test_123",
        symbol="BTC-USD",
        timeframe="1h",
        candle_close_time="2026-07-09T00:00:00Z",
        decision_state="EXECUTION_ENTRY",
        direction="BUY",
        alignment_type="TREND_FOLLOWING",
        entry=100.0,
        sl=95.0,
        tp1=110.0,
        tp2=120.0,
        rr_tp1=2.0,
        rr_tp2=4.0,
        confluence_score=80.0,
        directional_score=80.0,
        quality_score=80.0,
        market_bias="BULLISH",
        setup_direction="BUY",
        trigger_direction="BUY",
        execution_direction="BUY",
        smc_support_source="SMC",
        smc_resistance_source="SMC",
        data_quality_valid=1,
        is_actionable=1,
        outcome_status="PENDING",
        outcome_time=None,
        bars_to_outcome=None,
        realized_r_multiple=0.0,
        reasons=[],
        warnings=[],
        created_at="2026-07-09T00:00:00Z",
        primary_regime="BULL_TREND",
        regime_flags="",
        regime_score=1.0,
        volume_confirmation="CONFIRMED",
        vwap_alignment="ABOVE",
        bos_present=0,
        choch_present=0,
        fvg_present=0,
        liquidity_sweep_present=0,
        workspace_id="crypto_trading"
    )
    
    # Switch active to crypto_trading and insert signal
    set_active_workspace_id("crypto_trading")
    assert insert_signal(sig, TEST_DB) is True
    
    # Create the exact same signal (same ID) for futures_trading
    sig_futures = Signal(
        signal_id="sig_test_123",
        symbol="BTC-USD",
        timeframe="1h",
        candle_close_time="2026-07-09T00:00:00Z",
        decision_state="EXECUTION_ENTRY",
        direction="BUY",
        alignment_type="TREND_FOLLOWING",
        entry=100.0,
        sl=95.0,
        tp1=110.0,
        tp2=120.0,
        rr_tp1=2.0,
        rr_tp2=4.0,
        confluence_score=80.0,
        directional_score=80.0,
        quality_score=80.0,
        market_bias="BULLISH",
        setup_direction="BUY",
        trigger_direction="BUY",
        execution_direction="BUY",
        smc_support_source="SMC",
        smc_resistance_source="SMC",
        data_quality_valid=1,
        is_actionable=1,
        outcome_status="PENDING",
        outcome_time=None,
        bars_to_outcome=None,
        realized_r_multiple=0.0,
        reasons=[],
        warnings=[],
        created_at="2026-07-09T00:00:00Z",
        primary_regime="BULL_TREND",
        regime_flags="",
        regime_score=1.0,
        volume_confirmation="CONFIRMED",
        vwap_alignment="ABOVE",
        bos_present=0,
        choch_present=0,
        fvg_present=0,
        liquidity_sweep_present=0,
        workspace_id="futures_trading"
    )
    
    set_active_workspace_id("futures_trading")
    # Insertion should succeed because composite primary key is (signal_id, workspace_id)
    assert insert_signal(sig_futures, TEST_DB) is True
    
    # Verify crypto_trading only loads its own signals
    crypto_sigs = load_signals(TEST_DB, workspace_id="crypto_trading")
    assert len(crypto_sigs) == 1
    assert crypto_sigs[0].workspace_id == "crypto_trading"
    
    # Verify futures_trading only loads its own signals
    futures_sigs = load_signals(TEST_DB, workspace_id="futures_trading")
    assert len(futures_sigs) == 1
    assert futures_sigs[0].workspace_id == "futures_trading"

# Test 3: Alert log deduplication isolation
def test_alerts_isolation():
    # Insert alert for crypto_trading
    set_active_workspace_id("crypto_trading")
    assert insert_alert_log("sig_test_123", "discord", "SENT", db_path=TEST_DB) is True
    assert check_alert_exists("sig_test_123", "discord", TEST_DB) is True
    
    # Check if duplicate alert logic triggers for futures_trading workspace
    set_active_workspace_id("futures_trading")
    # Should not exist in futures_trading because they are isolated!
    assert check_alert_exists("sig_test_123", "discord", TEST_DB) is False

# Test 4: Playbook setting isolation
def test_playbook_isolation():
    pb_crypto = Playbook(
        playbook_id="pb_crypto",
        name="Crypto Playbook",
        enabled=1,
        min_confluence_score=75.0,
        workspace_id="crypto_trading"
    )
    save_playbook(pb_crypto, TEST_DB)
    
    pb_futures = Playbook(
        playbook_id="pb_futures",
        name="Futures Playbook",
        enabled=1,
        min_confluence_score=85.0,
        workspace_id="futures_trading"
    )
    save_playbook(pb_futures, TEST_DB)
    
    # Active playbook for crypto should load min confluence score of 75.0
    set_active_workspace_id("crypto_trading")
    active_pb = get_active_playbook(TEST_DB)
    assert active_pb.name == "Crypto Playbook"
    assert active_pb.min_confluence_score == 75.0
    
    # Active playbook for futures should load min confluence score of 85.0
    set_active_workspace_id("futures_trading")
    active_pb_fut = get_active_playbook(TEST_DB)
    assert active_pb_fut.name == "Futures Playbook"
    assert active_pb_fut.min_confluence_score == 85.0

# Test 5: Portfolio Settings isolation
def test_portfolio_settings_isolation():
    settings_crypto = PortfolioSettings(
        id=1,
        account_equity=50000.0,
        risk_per_trade_pct=2.0,
        workspace_id="crypto_trading"
    )
    assert save_portfolio_settings(settings_crypto, TEST_DB) is True
    
    settings_futures = PortfolioSettings(
        id=1,
        account_equity=150000.0,
        risk_per_trade_pct=0.5,
        workspace_id="futures_trading"
    )
    assert save_portfolio_settings(settings_futures, TEST_DB) is True
    
    # Load and assert
    set_active_workspace_id("crypto_trading")
    loaded_crypto = load_portfolio_settings(TEST_DB)
    assert loaded_crypto.account_equity == 50000.0
    assert loaded_crypto.risk_per_trade_pct == 2.0
    
    set_active_workspace_id("futures_trading")
    loaded_futures = load_portfolio_settings(TEST_DB)
    assert loaded_futures.account_equity == 150000.0
    assert loaded_futures.risk_per_trade_pct == 0.5

# Test 6: Scan Results / Runs isolation
def test_scan_results_isolation():
    run_crypto = ScanRun(
        scan_run_id="run_crypto_1",
        started_at="now", finished_at="now", status="SUCCESS",
        total_symbols=1, success_count=1, warning_count=0, error_count=0, skipped_count=0,
        config_json="{}", workspace_id="crypto_trading"
    )
    assert insert_scan_run(run_crypto, TEST_DB) is True
    
    res_crypto = ScanResult(
        scan_run_id="run_crypto_1", symbol="BTC-USD", timeframe="1h", scan_time="now",
        symbol_status="ACTIONABLE", decision_state="EXECUTION_ENTRY", direction="BUY", alignment_type="TF",
        confluence_score=80.0, rr_tp1=2.0, primary_regime="BULL", regime_flags_json="[]",
        data_quality_status="VALID", alert_status="SENT", journal_status="SAVED", reasons_json="[]",
        warnings_json="[]", error_message="", created_at="now", workspace_id="crypto_trading"
    )
    assert insert_scan_result(res_crypto, TEST_DB) is True
    
    run_futures = ScanRun(
        scan_run_id="run_futures_1",
        started_at="now", finished_at="now", status="SUCCESS",
        total_symbols=1, success_count=1, warning_count=0, error_count=0, skipped_count=0,
        config_json="{}", workspace_id="futures_trading"
    )
    assert insert_scan_run(run_futures, TEST_DB) is True
    
    # Assert runs isolation
    set_active_workspace_id("crypto_trading")
    crypto_runs = load_scan_runs(db_path=TEST_DB)
    assert len(crypto_runs) == 1
    assert crypto_runs[0].scan_run_id == "run_crypto_1"
    
    set_active_workspace_id("futures_trading")
    futures_runs = load_scan_runs(db_path=TEST_DB)
    assert len(futures_runs) == 1
    assert futures_runs[0].scan_run_id == "run_futures_1"

# Test 7: Watchlist isolation path resolution
def test_watchlist_file_isolation():
    # Save a custom watchlist for crypto_trading
    crypto_items = [{"symbol": "BTC-USD", "display_name": "Bitcoin", "asset_class": "Crypto", "enabled": True}]
    set_active_workspace_id("crypto_trading")
    assert save_watchlist(crypto_items, workspace_id="crypto_trading") is True
    
    # Save a custom watchlist for futures_trading
    futures_items = [{"symbol": "ES=F", "display_name": "S&P 500", "asset_class": "Indices", "enabled": True}]
    set_active_workspace_id("futures_trading")
    assert save_watchlist(futures_items, workspace_id="futures_trading") is True
    
    # Load and assert they retrieve different items
    loaded_crypto = load_watchlist(workspace_id="crypto_trading")
    assert len(loaded_crypto) == 1
    assert loaded_crypto[0]["symbol"] == "BTC-USD"
    
    loaded_futures = load_watchlist(workspace_id="futures_trading")
    assert len(loaded_futures) == 1
    assert loaded_futures[0]["symbol"] == "ES=F"
