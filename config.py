import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Загружаем переменные из .env.dev
# load_dotenv(".env.dev")  # ⚠️ на проде поменяешь на ".env.prod"
# class Config:
#     ENV = os.getenv("ENV", "dev")
#     BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Список админов (глобальных или всех)

    # ID каналов
    SWIM_CHANNEL_ID = int(os.getenv("SWIM_CHANNEL_ID"))
    AMATEUR_CHANNEL_ID = int(os.getenv("AMATEUR_CHANNEL_ID"))
    OPENWATER_CHANNEL_ID = int(os.getenv("OPENWATER_CHANNEL_ID"))
    GYM_CHANNEL_ID = int(os.getenv("GYM_CHANNEL_ID"))
    FUNCTIONAL_CHANNEL_ID = int(os.getenv("FUNCTIONAL_CHANNEL_ID"))


DB_NAME = os.getenv("DB_NAME", "reminder.db")