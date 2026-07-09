import datetime
from typing import Tuple
from tradenexus.playbook.playbook_models import Playbook, DailyTradingState

def validate_discipline_rules(playbook: Playbook, state: DailyTradingState, current_time_utc: datetime.datetime = None) -> Tuple[bool, str]:
    """
    Validates daily trading limits and cooldown rules.
    Returns (True, message) if passed, or (False, reason) if blocked.
    """
    if current_time_utc is None:
        current_time_utc = datetime.datetime.utcnow()
        
    # Check max trades per day
    if playbook.max_trades_per_day > 0 and state.trades_count >= playbook.max_trades_per_day:
        return False, f"Daily trade limit reached ({state.trades_count}/{playbook.max_trades_per_day})."
        
    # Check max losses per day
    if playbook.max_losses_per_day > 0 and state.losses_count >= playbook.max_losses_per_day:
        return False, f"Daily loss limit reached ({state.losses_count}/{playbook.max_losses_per_day})."
        
    # Check consecutive losses
    if playbook.max_consecutive_losses > 0 and state.consecutive_losses >= playbook.max_consecutive_losses:
        return False, f"Consecutive loss limit reached ({state.consecutive_losses}/{playbook.max_consecutive_losses})."
        
    # Check cooldown minutes after loss
    if playbook.cooldown_minutes_after_loss > 0 and state.last_loss_time:
        try:
            last_loss = datetime.datetime.fromisoformat(state.last_loss_time)
            diff_mins = (current_time_utc - last_loss).total_seconds() / 60.0
            if diff_mins < playbook.cooldown_minutes_after_loss:
                remaining = int(playbook.cooldown_minutes_after_loss - diff_mins)
                return False, f"Trading is cooling down after recent loss. {remaining} minutes remaining."
        except Exception:
            pass
            
    return True, "Daily trading limits and cooldown rules are satisfied."
