import requests
import logging

logger = logging.getLogger(__name__)

def send_line_notify(token: str, message: str) -> tuple[bool, str]:
    """
    Sends a notification via LINE Notify API.
    
    Args:
        token (str): LINE Notify Bearer Token.
        message (str): The alert message content.
        
    Returns:
        tuple[bool, str]: (Success status, Info or error message)
    """
    if not token:
        return False, "LINE Notify token is empty."
        
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {"message": message}
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            logger.info("LINE Notify sent successfully.")
            return True, "LINE Notify sent successfully."
        else:
            err_msg = f"LINE Notify failed with status code {response.status_code}: {response.text}"
            logger.error(err_msg)
            return False, err_msg
            
    except requests.exceptions.Timeout:
        logger.error("LINE Notify request timed out.")
        return False, "LINE Notify request timed out (10s)."
    except Exception as e:
        err_msg = f"LINE Notify error: {str(e)}"
        logger.error(err_msg)
        return False, err_msg

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> tuple[bool, str]:
    """
    Sends a message via Telegram Bot API.
    
    Args:
        bot_token (str): Telegram Bot Token (from BotFather).
        chat_id (str): Telegram Chat ID of recipient.
        message (str): The alert message content.
        
    Returns:
        tuple[bool, str]: (Success status, Info or error message)
    """
    if not bot_token or not chat_id:
        return False, "Telegram Bot Token or Chat ID is empty."
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if response.status_code == 200 and res_json.get("ok"):
            logger.info("Telegram message sent successfully.")
            return True, "Telegram message sent successfully."
        else:
            err_msg = f"Telegram failed with status code {response.status_code}: {res_json.get('description', response.text)}"
            logger.error(err_msg)
            return False, err_msg
            
    except requests.exceptions.Timeout:
        logger.error("Telegram request timed out.")
        return False, "Telegram request timed out (10s)."
    except Exception as e:
        err_msg = f"Telegram error: {str(e)}"
        logger.error(err_msg)
        return False, err_msg

def format_signal_message(ticker: str, timeframe: str, strategy: dict) -> str:
    """
    Formats the trading signal alert message with emojis for LINE/Telegram.
    
    Args:
        ticker (str): The asset symbol.
        timeframe (str): The timeframe of the signal.
        strategy (str): Strategy details from generate_trading_signal.
        
    Returns:
        str: Formatted message.
    """
    decision = strategy.get("Decision", "NEUTRAL")
    confidence = strategy.get("Confidence", 50)
    entry = strategy.get("Entry", 0.0)
    sl = strategy.get("StopLoss", 0.0)
    tp1 = strategy.get("TakeProfit1", 0.0)
    tp2 = strategy.get("TakeProfit2", 0.0)
    warning = strategy.get("Warning", "")
    
    # Emoji based on signal direction
    if "STRONG BUY" in decision:
        signal_emoji = "🟢🟢 [STRONG BUY]"
    elif "BUY" in decision:
        signal_emoji = "🟢 [BUY]"
    elif "STRONG SELL" in decision:
        signal_emoji = "🔴🔴 [STRONG SELL]"
    elif "SELL" in decision:
        signal_emoji = "🔴 [SELL]"
    else:
        signal_emoji = "⚪ [NEUTRAL]"
        
    # Clean HTML characters for Telegram parse_mode="HTML" compatibility
    clean_warning = warning.replace("<", "&lt;").replace(">", "&gt;")
        
    msg = f"""
<b>🔔 [TradeNexus Pro Signal Alert]</b>
━━━━━━━━━━━━━━━━━━
📈 <b>Asset:</b> {ticker}
⏱️ <b>Timeframe:</b> {timeframe}
🚦 <b>Signal:</b> {signal_emoji}
🎯 <b>Confidence:</b> {confidence}%
━━━━━━━━━━━━━━━━━━
🛒 <b>Entry Price:</b> ${entry:,.2f}
🛡️ <b>Stop Loss (SL):</b> ${sl:,.2f}
🟢 <b>Take Profit 1 (TP1):</b> ${tp1:,.2f}
🟢 <b>Take Profit 2 (TP2):</b> ${tp2:,.2f}
━━━━━━━━━━━━━━━━━━
ℹ️ <b>Market State:</b>
<i>{clean_warning}</i>
"""
    return msg.strip()
