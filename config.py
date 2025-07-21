import os
import json
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()


@dataclass
class Config:
    # Singleton pattern
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._load_env()
        return cls.__instance

    def _load_env(self):
        """Загрузка всех переменных окружения"""
        # Основные настройки
        self.ENV = os.getenv("ENV", "dev")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")

        # Платежи
        self.PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")
        self.CURRENCY = os.getenv("CURRENCY", "RUB")
        self.PRICE = int(os.getenv("PRICE", 15000))  # В копейках

        # ID каналов
        self.SWIM_CHANNEL_ID = int(os.getenv("SWIM_CHANNEL_ID"))
        self.AMATEUR_CHANNEL_ID = int(os.getenv("AMATEUR_CHANNEL_ID"))
        self.OPENWATER_CHANNEL_ID = int(os.getenv("OPENWATER_CHANNEL_ID"))
        self.GYM_CHANNEL_ID = int(os.getenv("GYM_CHANNEL_ID"))
        self.FUNCTIONAL_CHANNEL_ID = int(os.getenv("FUNCTIONAL_CHANNEL_ID"))

        # Настройки БД
        self.DB_NAME = os.getenv("DB_NAME", "reminder.db")

    @property
    def provider_data(self) -> str:
        """Генерация данных для платежной системы"""
        data = {
            "receipt": {
                "items": [{
                    "description": "Подписка на месяц",
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{self.PRICE / 100:.2f}",
                        "currency": self.CURRENCY
                    },
                    "vat_code": 1
                }]
            }
        }
        return json.dumps(data)

    @property
    def channel_ids(self) -> List[int]:
        """Все ID каналов в виде списка"""
        return [
            self.SWIM_CHANNEL_ID,
            self.AMATEUR_CHANNEL_ID,
            self.OPENWATER_CHANNEL_ID,
            self.GYM_CHANNEL_ID,
            self.FUNCTIONAL_CHANNEL_ID
        ]


# Синглтон экземпляр конфига
config = Config()
DB_NAME = config.DB_NAME
__all__ = ['config', 'DB_NAME']
