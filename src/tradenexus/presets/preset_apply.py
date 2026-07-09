import json
import datetime
import uuid
from typing import List, Dict, Any, Tuple
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord
from tradenexus.presets.preset_repository import log_apply_history
from tradenexus.playbook.playbook_models import Playbook
from tradenexus.playbook.playbook_repository import get_active_playbook, save_playbook
from tradenexus.portfolio.risk_models import PortfolioSettings
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings, save_portfolio_settings
from tradenexus.scanner.watchlist import load_watchlist, save_watchlist

def generate_preset_diff(
    preset: StrategyPreset,
    playbook: Playbook,
    portfolio: PortfolioSettings,
    watchlist: List[dict]
) -> dict:
    """
    Computes differences between active config and preset values.
    """
    diff = {
        "playbook": {},
        "portfolio": {},
        "watchlist": {}
    }
    
    playbook_fields = [
        ("allowed_symbols", playbook.allowed_symbols, preset.allowed_symbols),
        ("allowed_timeframes", playbook.allowed_timeframes, preset.allowed_timeframes),
        ("allowed_sessions", playbook.allowed_sessions, preset.allowed_sessions),
        ("allowed_setup_types", playbook.allowed_setup_types, preset.allowed_setup_types),
        ("min_confluence_score", playbook.min_confluence_score, preset.min_confluence_score),
        ("min_rr", playbook.min_rr, preset.min_rr),
        ("allowed_regimes", playbook.allowed_regimes, preset.allowed_regimes),
        ("blocked_regimes", playbook.blocked_regimes, preset.blocked_regimes),
        ("max_trades_per_day", playbook.max_trades_per_day, preset.max_trades_per_day),
        ("max_losses_per_day", playbook.max_losses_per_day, preset.max_losses_per_day),
        ("max_consecutive_losses", playbook.max_consecutive_losses, preset.max_consecutive_losses),
        ("cooldown_minutes_after_loss", playbook.cooldown_minutes_after_loss, preset.cooldown_minutes_after_loss)
    ]
    
    for field_name, curr_val, preset_val in playbook_fields:
        will_change = curr_val != preset_val
        diff["playbook"][field_name] = {
            "current": curr_val,
            "preset": preset_val,
            "will_change": will_change
        }
        
    portfolio_fields = [
        ("risk_per_trade_pct", portfolio.risk_per_trade_pct, preset.default_portfolio_risk_pct)
    ]
    
    for field_name, curr_val, preset_val in portfolio_fields:
        will_change = curr_val != preset_val
        diff["portfolio"][field_name] = {
            "current": curr_val,
            "preset": preset_val,
            "will_change": will_change
        }
        
    curr_symbols = {item.get("symbol") for item in watchlist if item.get("symbol")}
    missing_symbols = [s for s in preset.suggested_symbols if s not in curr_symbols]
    diff["watchlist"]["suggested_symbols"] = {
        "current": list(curr_symbols),
        "suggested_to_add": missing_symbols,
        "will_change": len(missing_symbols) > 0
    }
    
    return diff

def apply_preset(
    preset: StrategyPreset,
    workspace_id: str,
    apply_playbook: bool = True,
    apply_portfolio: bool = False,
    apply_watchlist: bool = False,
    db_path: str = None
) -> dict:
    """
    Applies selected sections of a StrategyPreset to the workspace settings.
    Saves apply history.
    """
    # 1. Fetch current settings
    playbook = get_active_playbook(db_path, workspace_id)
    if not playbook:
        # Create a default playbook for the workspace if missing
        playbook = Playbook(
            playbook_id="default_playbook",
            name="Default Playbook",
            workspace_id=workspace_id
        )
        
    portfolio = load_portfolio_settings(db_path, workspace_id)
    watchlist = load_watchlist(workspace_id=workspace_id)
    
    # 2. Generate diff preview for history logging
    diff = generate_preset_diff(preset, playbook, portfolio, watchlist)
    
    previous_values = {
        "playbook": {k: v["current"] for k, v in diff["playbook"].items()},
        "portfolio": {k: v["current"] for k, v in diff["portfolio"].items()},
        "watchlist": diff["watchlist"]["suggested_symbols"]["current"]
    }
    
    new_values = {}
    applied_sections = []
    warnings = []
    
    # 3. Apply Playbook settings
    if apply_playbook:
        playbook.allowed_symbols = list(preset.allowed_symbols)
        playbook.allowed_timeframes = list(preset.allowed_timeframes)
        playbook.allowed_sessions = list(preset.allowed_sessions)
        playbook.allowed_setup_types = list(preset.allowed_setup_types)
        playbook.min_confluence_score = preset.min_confluence_score
        playbook.min_rr = preset.min_rr
        playbook.allowed_regimes = list(preset.allowed_regimes)
        playbook.blocked_regimes = list(preset.blocked_regimes)
        playbook.max_trades_per_day = preset.max_trades_per_day
        playbook.max_losses_per_day = preset.max_losses_per_day
        playbook.max_consecutive_losses = preset.max_consecutive_losses
        playbook.cooldown_minutes_after_loss = preset.cooldown_minutes_after_loss
        playbook.active_preset_id = preset.preset_id
        
        save_playbook(playbook, db_path, workspace_id)
        applied_sections.append("playbook")
        new_values["playbook"] = {k: v["preset"] for k, v in diff["playbook"].items()}
        new_values["playbook"]["active_preset_id"] = preset.preset_id
        
    # 4. Apply Portfolio Settings
    if apply_portfolio:
        portfolio.risk_per_trade_pct = preset.default_portfolio_risk_pct
        save_portfolio_settings(portfolio, db_path, workspace_id)
        applied_sections.append("portfolio")
        new_values["portfolio"] = {k: v["preset"] for k, v in diff["portfolio"].items()}
        
    # 5. Apply Watchlist Suggestions (Append-only)
    if apply_watchlist:
        to_add = diff["watchlist"]["suggested_symbols"]["suggested_to_add"]
        if to_add:
            # Append-only: create default watchlist records for suggestions
            updated_watchlist = list(watchlist)
            for sym in to_add:
                updated_watchlist.append({
                    "symbol": sym,
                    "display_name": sym,
                    "asset_class": preset.asset_class,
                    "enabled": True,
                    "min_rr": 1.5,
                    "min_confluence": 70.0
                })
            save_watchlist(updated_watchlist, workspace_id=workspace_id)
            applied_sections.append("watchlist")
            new_values["watchlist"] = [item.get("symbol") for item in updated_watchlist]
        else:
            new_values["watchlist"] = previous_values["watchlist"]
            warnings.append("No new suggested symbols to append to watchlist.")
            
    # 6. Log Apply History Record
    apply_id = str(uuid.uuid4())
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    
    record = PresetApplyRecord(
        apply_id=apply_id,
        preset_id=preset.preset_id,
        workspace_id=workspace_id,
        applied_at=now_str,
        applied_sections=applied_sections,
        previous_values=json.dumps(previous_values),
        new_values=json.dumps(new_values),
        warnings=warnings,
        applied_by_label="System UI"
    )
    log_apply_history(record, db_path)
    
    return {
        "apply_id": apply_id,
        "applied_sections": applied_sections,
        "warnings": warnings,
        "previous_values": previous_values,
        "new_values": new_values
    }
