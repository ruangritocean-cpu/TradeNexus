import logging
from typing import Dict, Any, Tuple
from tradenexus.alerts.dispatcher import format_alert_message

logger = logging.getLogger(__name__)

def check_alert_configuration(
    discord_webhook: str = None,
    tg_bot_token: str = None,
    tg_chat_id: str = None
) -> Dict[str, Any]:
    """
    Validates configuration values for alerts.
    """
    providers = {}
    
    # Discord
    if discord_webhook:
        if "discord.com/api/webhooks" in discord_webhook:
            providers["discord"] = "CONFIGURED"
        else:
            providers["discord"] = "INVALID_URL"
    else:
        providers["discord"] = "NOT_CONFIGURED"
        
    # Telegram
    if tg_bot_token and tg_chat_id:
        providers["telegram"] = "CONFIGURED"
    elif tg_bot_token or tg_chat_id:
        providers["telegram"] = "PARTIALLY_CONFIGURED"
    else:
        providers["telegram"] = "NOT_CONFIGURED"
        
    return providers

def simulate_dry_run_alert(
    symbol: str,
    timeframe: str,
    strategy: dict
) -> str:
    """
    Generates notification message payload for verification without sending or DB writes.
    """
    msg = format_alert_message(symbol, timeframe, strategy)
    return msg
