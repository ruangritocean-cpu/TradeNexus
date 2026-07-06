import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> tuple[bool, str]:
    """
    Sends a message via Telegram Bot API with HTML parsing.
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
