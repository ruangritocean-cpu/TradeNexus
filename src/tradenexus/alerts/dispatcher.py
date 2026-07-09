import logging
import datetime
from tradenexus.alerts.telegram import send_telegram_message
from tradenexus.alerts.discord import send_discord_webhook
from tradenexus.journal.repository import check_alert_exists, insert_alert_log

logger = logging.getLogger(__name__)

def format_alert_message(ticker: str, timeframe: str, strategy: dict) -> str:
    """
    Formats a comprehensive unified alert message payload.
    Supports simple HTML tags for bold/italics.
    """
    decision = strategy.get("Decision", "NEUTRAL")
    direction = strategy.get("Direction", "NEUTRAL")
    alignment = strategy.get("AlignmentType", "CONFLICTED")
    entry = strategy.get("Entry", 0.0)
    sl = strategy.get("StopLoss", 0.0)
    tp1 = strategy.get("TakeProfit1", 0.0)
    tp2 = strategy.get("TakeProfit2", 0.0)
    rr_tp1 = strategy.get("RR_TP1", 0.0)
    conf_score = strategy.get("ConfluenceScore", 0.0)
    regime = strategy.get("Regime", "UNKNOWN")
    
    reasons = strategy.get("Reasons", [])
    warnings = strategy.get("Warnings", [])
    
    reasons_str = "\n".join([f"• {r}" for r in reasons]) if reasons else "None"
    warnings_str = "\n".join([f"• {w}" for w in warnings]) if warnings else "None"
    
    msg = f"""<b>TradeNexus Signal Alert</b>
──────────────────
<b>Asset:</b> {ticker}
<b>Timeframe:</b> {timeframe}
<b>Decision:</b> {decision} ({direction})
<b>Alignment Type:</b> {alignment}
<b>Market Regime:</b> {regime}
<b>Confluence Score:</b> {conf_score:.1f}%

<b>Entry Zone:</b> ${entry:,.2f}
<b>Stop Loss (SL):</b> ${sl:,.2f}
<b>Take Profit 1 (TP1):</b> ${tp1:,.2f} (RR: {rr_tp1:.2f})
<b>Take Profit 2 (TP2):</b> ${tp2:,.2f}

<b>Confluence Drivers:</b>
{reasons_str}

<b>Warnings/Risk Vetoes:</b>
{warnings_str}

<i>Note: Decision support only, not an automatic trading command.</i>"""

    try:
        from tradenexus.explain.decision_brief import generate_decision_brief
        from tradenexus.explain.templates import format_alert_brief
        
        brief_data = {
            "symbol": ticker,
            "timeframe": timeframe,
            "decision_state": decision,
            "direction": direction,
            "alignment_type": alignment,
            "confluence_score": conf_score,
            "primary_regime": regime,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "rr_tp1": rr_tp1,
            "warnings": warnings
        }
        brief = generate_decision_brief(brief_data)
        brief_text = format_alert_brief(brief)
        msg += f"\n\n<b>📝 Decision Brief Summary:</b>\n{brief_text}"
    except Exception as e:
        logger.warning(f"Failed to generate brief for alert message: {str(e)}")

    return msg

def dispatch_alert(
    signal_id: str,
    ticker: str,
    timeframe: str,
    strategy: dict,
    discord_webhook_url: str = None,
    tg_bot_token: str = None,
    tg_chat_id: str = None,
    db_path: str = None
) -> dict:
    """
    Dispatches alerts to Discord and Telegram.
    Checks alert_log database to prevent duplicate alerts per provider.
    
    Returns:
        dict: Status of each provider {"discord": bool, "telegram": bool}
    """
    results = {"discord": "NOT_CONFIGURED", "telegram": "NOT_CONFIGURED"}
    alert_msg = format_alert_message(ticker, timeframe, strategy)
    
    # 1. Discord Dispatch
    if discord_webhook_url:
        provider = "discord"
        # Check if already sent
        if check_alert_exists(signal_id, provider, db_path):
            logger.info(f"Discord alert already exists for signal {signal_id}. Skipping.")
            results["discord"] = "SKIPPED_DUPLICATE"
        else:
            success, err_msg = send_discord_webhook(discord_webhook_url, alert_msg)
            if success:
                insert_alert_log(signal_id, provider, "SENT", db_path=db_path)
                results["discord"] = "SENT"
            else:
                logger.error(f"Failed to dispatch Discord alert: {err_msg}")
                results["discord"] = "FAILED"
                
    # 2. Telegram Dispatch
    if tg_bot_token and tg_chat_id:
        provider = "telegram"
        if check_alert_exists(signal_id, provider, db_path):
            logger.info(f"Telegram alert already exists for signal {signal_id}. Skipping.")
            results["telegram"] = "SKIPPED_DUPLICATE"
        else:
            success, err_msg = send_telegram_message(tg_bot_token, tg_chat_id, alert_msg)
            if success:
                insert_alert_log(signal_id, provider, "SENT", db_path=db_path)
                results["telegram"] = "SENT"
            else:
                logger.error(f"Failed to dispatch Telegram alert: {err_msg}")
                results["telegram"] = "FAILED"
                
    return results
