import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_CHAT_IDS = list(map(int, os.getenv("ADMIN_CHAT_IDS", "").split(",")))

    # Словарь всех каналов по ключам
    CHANNELS = {
        "swimmasters": {
            "id": int(os.getenv("SWIM_CHANNEL_ID")),
            "title": "SwimGlide Masters 🏊",
            "description": "Тренировки для опытных спортсменов 3 раза в неделю",
        },
        "amateur": {
            "id": int(os.getenv("AMATEUR_CHANNEL_ID")),
            "title": "SwimGlide Amateur 👙",
            "description": "Тренировки для начинающих и любителей 3 раза в неделю",
        }
    }