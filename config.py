import os
from dotenv import load_dotenv

load_dotenv()

class Сonfig:
    ENV = os.getenv("ENV", "dev")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")

    # Список админов (глобальных или всех)

    # ID каналов
    SWIM_CHANNEL_ID = int(os.getenv("SWIM_CHANNEL_ID"))
    AMATEUR_CHANNEL_ID = int(os.getenv("AMATEUR_CHANNEL_ID"))
    OPENWATER_CHANNEL_ID = int(os.getenv("OPENWATER_CHANNEL_ID"))
    GYM_CHANNEL_ID = int(os.getenv("GYM_CHANNEL_ID"))
    FUNCTIONAL_CHANNEL_ID = int(os.getenv("FUNCTIONAL_CHANNEL_ID"))

config = Config()
DB_NAME = os.getenv("DB_NAME", "reminder.db")
