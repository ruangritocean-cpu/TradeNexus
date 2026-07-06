import logging
import datetime
import json
from typing import List, Dict, Any
from tradenexus.journal.db import get_db_connection
from tradenexus.portfolio.risk_models import ExposureSummary, PortfolioSettings, SymbolRiskProfile
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings, load_symbol_profile

logger = logging.getLogger(__name__)

def _get_row_val(r, col, default):
    try:
        val = r[col]
        return val if val is not None else default
    except Exception:
        return default

def calculate_portfolio_exposure(
    db_path: str = None,
    settings: PortfolioSettings = None
) -> ExposureSummary:
    """
    Aggregates current portfolio exposure from active trades, outcomes, and setups.
    Deduplicates to prevent double-counting.
    """
    if settings is None:
        settings = load_portfolio_settings(db_path)
        
    equity = settings.account_equity
    risk_per_trade = equity * (settings.risk_per_trade_pct / 100.0)
    
    conn = get_db_connection(db_path)
    
    realized_daily_risk = 0.0
    total_open_risk = 0.0
    potential_setup_risk = 0.0
    
    active_trade_count = 0
    actionable_setup_count = 0
    
    risk_by_symbol = {}
    risk_by_asset_class = {}
    risk_by_direction = {"BUY": 0.0, "SELL": 0.0}
    
    # Store tracked signal_ids and trade_ids to avoid double-counting
    seen_signal_ids = set()
    seen_trade_ids = set()
    
    try:
        cursor = conn.cursor()
        
        # 1. Calculate realized daily loss/profit from trades closed today (UTC)
        today_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED' AND closed_at LIKE ?", (f"{today_date}%",))
        closed_rows = cursor.fetchall()
        for r in closed_rows:
            r_multiple = _get_row_val(r, "realized_r_multiple", 0.0)
            # Realized risk/reward = R multiple * dollar risk per trade
            realized_daily_risk += r_multiple * risk_per_trade
            
        # 2. Get active open trades
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        open_rows = cursor.fetchall()
        for r in open_rows:
            trade_id = r["trade_id"]
            if trade_id in seen_trade_ids:
                continue
            seen_trade_ids.add(trade_id)
            
            sig_id = _get_row_val(r, "signal_id", None)
            if sig_id:
                seen_signal_ids.add(sig_id)
                
            symbol = r["symbol"]
            direction = r["direction"]
            entry = r["entry"]
            sl = r["sl"]
            
            # Load symbol profile for asset class, multiplier, point value
            prof = load_symbol_profile(symbol, db_path)
            mult = prof.contract_multiplier if prof else settings.default_contract_multiplier
            pv = prof.point_value if prof else settings.default_point_value
            asset_class = prof.asset_class if prof else "Unknown"
            
            # Determine size units or assume default 1.0 R risk
            # For exposure calculation, if size is not recorded or 0, we treat it as 1.0 R risk budget
            pts_risk = abs(entry - sl)
            unit_risk = pts_risk * mult * pv
            
            # Estimate trade size if not saved (assuming standard risk budget)
            units = (risk_per_trade / unit_risk) if unit_risk > 0 else 1.0
            trade_risk = units * unit_risk if unit_risk > 0 else risk_per_trade
            
            total_open_risk += trade_risk
            active_trade_count += 1
            
            # Grouping
            risk_by_symbol[symbol] = risk_by_symbol.get(symbol, 0.0) + trade_risk
            risk_by_asset_class[asset_class] = risk_by_asset_class.get(asset_class, 0.0) + trade_risk
            risk_by_direction[direction] = risk_by_direction.get(direction, 0.0) + trade_risk
            
        # 3. Calculate potential setup risk from latest scan results
        # Get latest scan run
        cursor.execute("SELECT scan_run_id FROM scan_runs ORDER BY started_at DESC LIMIT 1")
        run_row = cursor.fetchone()
        if run_row:
            run_id = run_row["scan_run_id"]
            cursor.execute("SELECT * FROM scan_results WHERE scan_run_id = ?", (run_id,))
            scan_rows = cursor.fetchall()
            
            for r in scan_rows:
                state = r["decision_state"]
                sig_id = _get_row_val(r, "signal_id", None)
                
                # Deduplicate setups with active trades or duplicate signals
                if sig_id and sig_id in seen_signal_ids:
                    continue
                    
                if state in ["ENTRY TRIGGERED", "READY"]:
                    if sig_id:
                        seen_signal_ids.add(sig_id)
                        
                    symbol = r["symbol"]
                    direction = r["direction"]
                    
                    prof = load_symbol_profile(symbol, db_path)
                    asset_class = prof.asset_class if prof else "Unknown"
                    
                    potential_setup_risk += risk_per_trade
                    actionable_setup_count += 1
                    
                    risk_by_symbol[symbol] = risk_by_symbol.get(symbol, 0.0) + risk_per_trade
                    risk_by_asset_class[asset_class] = risk_by_asset_class.get(asset_class, 0.0) + risk_per_trade
                    risk_by_direction[direction] = risk_by_direction.get(direction, 0.0) + risk_per_trade
                    
    except Exception as e:
        logger.error(f"Error calculating portfolio exposure: {str(e)}")
    finally:
        conn.close()
        
    open_pct = (total_open_risk / equity * 100.0) if equity > 0 else 0.0
    setup_pct = (potential_setup_risk / equity * 100.0) if equity > 0 else 0.0
    
    same_dir_trades = 0
    # count active trades with same direction as most recent signal
    # we can simplify: return same direction trades count as max trades count on either side
    same_dir_trades = max(len([r for r in open_rows if r["direction"] == "BUY"]), len([r for r in open_rows if r["direction"] == "SELL"])) if 'open_rows' in locals() else 0
    
    return ExposureSummary(
        realized_daily_risk=realized_daily_risk,
        total_open_risk=total_open_risk,
        total_open_risk_pct=open_pct,
        potential_setup_risk=potential_setup_risk,
        potential_setup_risk_pct=setup_pct,
        risk_by_symbol=risk_by_symbol,
        risk_by_asset_class=risk_by_asset_class,
        risk_by_direction=risk_by_direction,
        number_of_active_trades=active_trade_count,
        same_direction_trade_count=same_dir_trades,
        pending_actionable_setup_count=actionable_setup_count
    )
