import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID"))
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID"))