import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Настройка логирования для всего проекта"""
    # Основной логгер
    logger = logging.getLogger()  # Корневой логгер

    # Очищаем существующие обработчики (если есть)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Формат сообщений
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Файловый обработчик (только ERROR и выше)
    file_handler = RotatingFileHandler(
        "bot.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)

    # Консольный обработчик (DEBUG и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)  # Минимальный уровень для всех обработчиков