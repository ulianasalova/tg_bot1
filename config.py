import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Список админов (глобальных или всех)

    # ID каналов
    SWIM_CHANNEL_ID = int(os.getenv("SWIM_CHANNEL_ID"))
    AMATEUR_CHANNEL_ID = int(os.getenv("AMATEUR_CHANNEL_ID"))
    OPENWATER_CHANNEL_ID = int(os.getenv("OPENWATER_CHANNEL_ID"))
    GYM_CHANNEL_ID = int(os.getenv("GYM_CHANNEL_ID"))
    FUNCTIONAL_CHANNEL_ID = int(os.getenv("FUNCTIONAL_CHANNEL_ID"))
    # Все каналы
    CHANNELS = {
        "swimmasters": {
            "id": SWIM_CHANNEL_ID,
            "title": "SwimGlide Masters 🥇",
            "description": "Тренировки по плаванию для опытных спортсменов 3 раза в неделю",
        },
        "amateur": {
            "id": AMATEUR_CHANNEL_ID,
            "title": "SwimGlide Amateur 🏊",
            "description": "Тренировки для начинающих и любителей 3 раза в неделю",
        },
        "open_water": {
            "id": OPENWATER_CHANNEL_ID,
            "title": "SwimGlide Open water 🏊",
            "description": "Тренировки для подготовки к заплывам на открытой воде",
        },
        "gym": {
            "id": GYM_CHANNEL_ID,
            "title": "SwimGlide GYM 💪",
            "description": "Силовые тренировки в зале для пловцов",
        },
        "functional": {
            "id": FUNCTIONAL_CHANNEL_ID,
            "title": "SwimGlide Functional 🌊 ",
            "description": "Функциональные тренировки для пловцов на каждый день",
        }
    }

DB_NAME = os.getenv("DB_NAME", "reminder.db")