import pytest
import datetime
import tempfile
import os
import json
from tradenexus.playbook.playbook_models import Playbook, PlaybookRuleEvent, DailyTradingState
from tradenexus.playbook.playbook_repository import (
    save_playbook, load_playbooks, get_active_playbook, log_playbook_rule_event,
    load_playbook_rule_events, get_daily_trading_state, save_daily_trading_state
)
from tradenexus.playbook.session_rules import get_current_sessions, validate_session_rule
from tradenexus.playbook.discipline_rules import validate_discipline_rules
from tradenexus.playbook.rule_engine import evaluate_playbook_rules
from tradenexus.playbook.playbook_explain import generate_playbook_summary
from tradenexus.journal.db import init_db

@pytest.fixture
def temp_db():
    # Setup temporary file database for testing
    fd, path = tempfile.mkstemp()
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass

def test_playbook_repository_crud(temp_db):
    pb = Playbook(
        playbook_id="test_pb",
        name="Test Dynamic Playbook",
        allowed_symbols=["AAPL", "TSLA"],
        min_confluence_score=80.0
    )
    save_playbook(pb, temp_db)
    
    loaded = load_playbooks(temp_db)
    assert len(loaded) >= 1
    assert loaded[0].playbook_id == "test_pb"
    assert loaded[0].name == "Test Dynamic Playbook"
    assert loaded[0].min_confluence_score == 80.0
    assert "AAPL" in loaded[0].allowed_symbols

def test_active_playbook_auto_initialization(temp_db):
    # If no playbook exists, get_active_playbook should initialize default
    active = get_active_playbook(temp_db)
    assert active is not None
    assert active.playbook_id == "default_playbook"

def test_session_rules():
    # Asian Session: 00:00 - 09:00 UTC
    dt_asia = datetime.datetime.utcnow().replace(hour=4)
    sessions = get_current_sessions(dt_asia)
    assert "ASIAN" in sessions
    
    # Test session validate matching
    ok, msg = validate_session_rule(["ASIAN"], dt_asia)
    assert ok
    
    # Test session validate mismatch
    ok, msg = validate_session_rule(["NEWYORK"], dt_asia)
    assert not ok

def test_daily_discipline_limits():
    playbook = Playbook(
        playbook_id="test_discipline",
        name="Discipline Playbook",
        max_trades_per_day=3,
        max_losses_per_day=2,
        max_consecutive_losses=2,
        cooldown_minutes_after_loss=30
    )
    
    # State satisfying limits
    state = DailyTradingState(
        date="2026-07-09",
        trades_count=1,
        losses_count=0,
        consecutive_losses=0
    )
    
    ok, msg = validate_discipline_rules(playbook, state)
    assert ok
    
    # Exceeded max trades limit
    state.trades_count = 3
    ok, msg = validate_discipline_rules(playbook, state)
    assert not ok
    assert "Daily trade limit reached" in msg
    
    # Active Cooldown
    state.trades_count = 2
    state.last_loss_time = datetime.datetime.utcnow().isoformat()
    ok, msg = validate_discipline_rules(playbook, state)
    assert not ok
    assert "cooling down" in msg

def test_rule_engine_evaluation(temp_db):
    playbook = Playbook(
        playbook_id="engine_pb",
        name="Engine Playbook",
        allowed_symbols=["BTC-USD"],
        allowed_timeframes=["1h"],
        allowed_setup_types=["TREND_FOLLOWING"],
        min_confluence_score=70.0,
        min_rr=1.5,
        allowed_sessions=["LONDON", "NEWYORK"]
    )
    
    # 1. Blocked setup - disallowed symbol
    mock_time = datetime.datetime.utcnow().replace(hour=14) # London/NY overlap
    status, passed, warnings, violations = evaluate_playbook_rules(
        playbook=playbook,
        symbol="AAPL",
        timeframe="1h",
        setup_type="TREND_FOLLOWING",
        confluence_score=75.0,
        rr=2.0,
        market_regime="TRENDING_UP",
        current_time_utc=mock_time,
        db_path=temp_db
    )
    assert status == "BLOCKED"
    assert any("AAPL is not in allowed list" in v for v in violations)
    
    # 2. Blocked setup - poor confluence
    status, passed, warnings, violations = evaluate_playbook_rules(
        playbook=playbook,
        symbol="BTC-USD",
        timeframe="1h",
        setup_type="TREND_FOLLOWING",
        confluence_score=65.0,
        rr=2.0,
        market_regime="TRENDING_UP",
        current_time_utc=mock_time,
        db_path=temp_db
    )
    assert status == "BLOCKED"
    assert any("Confluence score" in v for v in violations)

def test_playbook_nlp_explanation():
    summary_pass = generate_playbook_summary("PASS", ["Symbol is allowed", "RR satisfies requirement"], [], [])
    assert "🛡️ **Playbook Verification: PASS" in summary_pass
    assert "Passed Rules" in summary_pass
    
    summary_block = generate_playbook_summary("BLOCKED", [], [], ["Daily loss limit reached"])
    assert "🚫 **Playbook Verification: BLOCKED" in summary_block
    assert "Daily loss limit reached" in summary_block

def test_event_logging_persistence(temp_db):
    event = PlaybookRuleEvent(
        event_id="evt_test_99",
        created_at=datetime.datetime.utcnow().isoformat(),
        playbook_id="default_playbook",
        symbol="ETH-USD",
        rule_name="confluence_guard",
        event_type="VIOLATION",
        decision_state="BLOCKED",
        details_json=json.dumps({"reason": "test"})
    )
    log_playbook_rule_event(event, temp_db)
    
    events = load_playbook_rule_events(10, temp_db)
    assert len(events) == 1
    assert events[0].event_id == "evt_test_99"
    assert events[0].symbol == "ETH-USD"
    assert "reason" in json.loads(events[0].details_json)

from unittest.mock import patch, MagicMock
import pandas as pd

@patch("tradenexus.scanner.scan_engine.fetch_ohlcv_data")
@patch("tradenexus.scanner.scan_engine.calculate_confluence_score")
@patch("tradenexus.scanner.scan_engine.validate_trade_risk")
@patch("tradenexus.scanner.scan_engine.evaluate_mtf_hierarchy")
@patch("tradenexus.scanner.scan_engine.apply_regime_decision_rules")
def test_scanner_playbook_blocked_alert_status(
    mock_regime_rules, mock_mtf, mock_risk, mock_conf, mock_fetch, temp_db
):
    # Save a playbook that blocks BTC-USD
    playbook = Playbook(
        playbook_id="default_playbook",
        name="Blocker Playbook",
        enabled=1,
        allowed_symbols=["ETH-USD"], # BTC-USD is not allowed!
        min_confluence_score=70.0,
        min_rr=1.5
    )
    save_playbook(playbook, temp_db)
    
    # Mock watchlist path
    import tempfile
    fd, wl_path = tempfile.mkstemp()
    os.close(fd)
    
    import json
    wl_data = [
        {"symbol": "BTC-USD", "display_name": "Bitcoin", "enabled": True, "preferred_timeframes": ["1h"], "min_confluence_score": 70.0, "min_rr": 1.5, "alert_enabled": True}
    ]
    with open(wl_path, "w") as f:
        json.dump(wl_data, f)
        
    dates = pd.date_range("2026-01-01 00:00:00", periods=110, freq="h")
    df_mock = pd.DataFrame({
        "Open": [100.0] * 110,
        "High": [102.0] * 110,
        "Low": [98.0] * 110,
        "Close": [101.0] * 110,
        "Volume": [1000.0] * 110
    }, index=dates)
    
    mock_fetch.return_value = (df_mock, "")
    mock_conf.return_value = {
        "confluence_score": 80.0,
        "directional_score": 80.0,
        "quality_score": 80.0,
        "reasons": [],
        "warnings": []
    }
    mock_risk.return_value = {
        "Vetoed": False,
        "Entry": 100.0,
        "StopLoss": 95.0,
        "TakeProfit1": 110.0,
        "TakeProfit2": 120.0,
        "RR_TP1": 2.0,
        "RR_TP2": 4.0,
        "R_Vetoed": 0
    }
    mock_mtf.return_value = {
        "alignment_type": "TREND_FOLLOWING",
        "reasons": [],
        "warnings": []
    }
    mock_regime_rules.return_value = ("ENTRY TRIGGERED", [], [])
    
    from tradenexus.scanner.scan_engine import run_watchlist_scan
    res = run_watchlist_scan(db_path=temp_db, watchlist_path=wl_path, force_all_candles=True)
    
    # Check results: alert_status must be BLOCKED_BY_PLAYBOOK
    from tradenexus.scanner.scan_repository import load_scan_results_for_run
    results = load_scan_results_for_run(res["scan_run_id"], db_path=temp_db)
    assert len(results) == 1
    assert results[0].symbol == "BTC-USD"
    assert results[0].decision_state == "ENTRY TRIGGERED" # does not mutate c_state
    assert results[0].alert_status == "BLOCKED_BY_PLAYBOOK" # blocked alert status
    
    try:
        os.remove(wl_path)
    except OSError:
        pass


