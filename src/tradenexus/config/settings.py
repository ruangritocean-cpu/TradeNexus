import os

# Project root paths
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
WATCHLIST_FILE_PATH = os.path.join(DATA_DIR, "watchlist.json")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "tradenexus_journal.sqlite")

# Alert settings loaded from Environment variables (if any)
DISCORD_WEBHOOK_URL = os.environ.get("TRADENEXUS_DISCORD_WEBHOOK", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TRADENEXUS_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TRADENEXUS_TELEGRAM_CHAT_ID", "")
