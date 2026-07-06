import requests
import logging

logger = logging.getLogger(__name__)

def send_discord_webhook(webhook_url: str, message: str) -> tuple[bool, str]:
    """
    Sends a message via Discord Webhook.
    Converts simple HTML tags (<b>, <i>) to Discord-compatible Markdown (*, **).
    """
    if not webhook_url:
        return False, "Discord Webhook URL is empty."
        
    # Convert HTML styling to Discord Markdown
    markdown_message = message
    markdown_message = markdown_message.replace("<b>", "**").replace("</b>", "**")
    markdown_message = markdown_message.replace("<i>", "*").replace("</i>", "*")
    
    # Strip any other remaining HTML tags (like <u> or ━━━━)
    markdown_message = markdown_message.replace("━━━━━━━━━━━━━━━━━━", "──────────────────")
    
    payload = {"content": markdown_message}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            logger.info("Discord webhook alert sent successfully.")
            return True, "Discord Webhook sent successfully."
        else:
            err_msg = f"Discord Webhook failed with status code {response.status_code}: {response.text}"
            logger.error(err_msg)
            return False, err_msg
            
    except requests.exceptions.Timeout:
        logger.error("Discord Webhook request timed out.")
        return False, "Discord Webhook request timed out (10s)."
    except Exception as e:
        err_msg = f"Discord Webhook error: {str(e)}"
        logger.error(err_msg)
        return False, err_msg
