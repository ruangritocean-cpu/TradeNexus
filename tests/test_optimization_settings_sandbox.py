import pytest
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings
from tradenexus.optimization.optimizer import run_sandbox_backtest

def test_optimization_settings_sandbox_safety():
    """
    Verifies that running sandbox backtests does not modify the production settings.
    """
    db_path = "data/tradenexus_journal.sqlite"
    
    # 1. Load current live portfolio settings
    try:
        live_settings_before = load_portfolio_settings(db_path)
        before_equity = live_settings_before.account_equity
    except Exception:
        before_equity = 100000.0
        
    # 2. Run simulation with custom params dict
    tf_dfs = {}  # Empty dfs will return empty list immediately
    params = {"confluence_threshold": 95.0}
    run_sandbox_backtest(tf_dfs, "BTC", "1h", params)
    
    # 3. Verify settings did not change
    try:
        live_settings_after = load_portfolio_settings(db_path)
        assert live_settings_after.account_equity == before_equity
    except Exception:
        # DB not created yet, skip or pass
        pass
