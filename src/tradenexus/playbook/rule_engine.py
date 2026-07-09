import uuid
import datetime
import json
from typing import List, Tuple
from tradenexus.playbook.playbook_models import Playbook, PlaybookRuleEvent
from tradenexus.playbook.playbook_repository import get_daily_trading_state, log_playbook_rule_event
from tradenexus.playbook.session_rules import validate_session_rule
from tradenexus.playbook.discipline_rules import validate_discipline_rules

def evaluate_playbook_rules(
    playbook: Playbook,
    symbol: str,
    timeframe: str,
    setup_type: str,
    confluence_score: float,
    rr: float,
    market_regime: str,
    current_time_utc: datetime.datetime = None,
    db_path: str = None
) -> Tuple[str, List[str], List[str], List[str]]:
    """
    Evaluates playbook rules for a potential setup.
    Returns (status, passed_rules, warnings, violations)
    """
    if current_time_utc is None:
        current_time_utc = datetime.datetime.utcnow()
        
    passed_rules = []
    warnings = []
    violations = []
    
    # 1. Allowed Symbols Filter
    if playbook.allowed_symbols:
        if symbol not in playbook.allowed_symbols:
            violations.append(f"Symbol {symbol} is not in allowed list.")
        else:
            passed_rules.append(f"Symbol {symbol} is allowed.")
            
    # 2. Allowed Timeframes Filter
    if playbook.allowed_timeframes:
        if timeframe not in playbook.allowed_timeframes:
            violations.append(f"Timeframe {timeframe} is not in allowed list.")
        else:
            passed_rules.append(f"Timeframe {timeframe} is allowed.")
            
    # 3. Allowed Setup Types Filter
    if playbook.allowed_setup_types:
        if setup_type not in playbook.allowed_setup_types:
            violations.append(f"Setup type {setup_type} is not in allowed list.")
        else:
            passed_rules.append(f"Setup type {setup_type} is allowed.")
            
    # 4. Confluence Score Guard
    if confluence_score < playbook.min_confluence_score:
        violations.append(f"Confluence score ({confluence_score}) is below minimum ({playbook.min_confluence_score}).")
    else:
        passed_rules.append("Confluence score satisfies requirement.")
        
    # 5. Risk-to-Reward Ratio Guard
    if rr < playbook.min_rr:
        violations.append(f"Risk-to-Reward ratio ({rr:.2f}) is below minimum ({playbook.min_rr:.2f}).")
    else:
        passed_rules.append("RR ratio satisfies requirement.")
        
    # 6. Regime Filter (Allowed / Blocked)
    if playbook.allowed_regimes and market_regime not in playbook.allowed_regimes:
        violations.append(f"Market regime {market_regime} is not in allowed list.")
    elif playbook.blocked_regimes and market_regime in playbook.blocked_regimes:
        violations.append(f"Market regime {market_regime} is blocked.")
    else:
        passed_rules.append("Market regime satisfies playbook regime rules.")
        
    # 7. Session Hours Rule
    session_ok, session_msg = validate_session_rule(playbook.allowed_sessions, current_time_utc)
    if not session_ok:
        violations.append(session_msg)
    else:
        passed_rules.append(session_msg)
        
    # 8. Daily Limits & Cooldowns
    date_str = current_time_utc.strftime("%Y-%m-%d")
    state = get_daily_trading_state(date_str, db_path)
    disc_ok, disc_msg = validate_discipline_rules(playbook, state, current_time_utc)
    if not disc_ok:
        violations.append(disc_msg)
    else:
        passed_rules.append(disc_msg)
        
    # Compute overall status
    if violations:
        status = "BLOCKED"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASS"
        
    # Log any violations to database events
    for violation in violations:
        event = PlaybookRuleEvent(
            event_id=str(uuid.uuid4()),
            created_at=current_time_utc.isoformat(),
            playbook_id=playbook.playbook_id,
            symbol=symbol,
            rule_name="playbook_rule_check",
            event_type="VIOLATION",
            decision_state=status,
            details_json=json.dumps({
                "message": violation,
                "timeframe": timeframe,
                "setup_type": setup_type,
                "confluence_score": confluence_score,
                "rr": rr,
                "market_regime": market_regime
            })
        )
        try:
            log_playbook_rule_event(event, db_path)
        except Exception:
            pass
            
    return status, passed_rules, warnings, violations
