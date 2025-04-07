import asyncio
import nest_asyncio
nest_asyncio.apply()
from telegram.ext import ApplicationBuilder
from config import Config
from db import init_db
from handlers.start import get_start_handler
from handlers.admin import get_admin_handlers
from handlers.buttons import get_button_handler
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from utils.scheduler import start_scheduler, send_reminders


# Устанавливаем команды
async def setup_bot_commands(app):
    # Команды для всех пользователей
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
        ],
        scope=BotCommandScopeDefault()
    )

    # Команды для админа
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
            BotCommand("invite", "📩 Приглашение в канал"),
            BotCommand("pin_invite", "📌 Закрепить приглашение"),
            BotCommand("broadcast", "📢 Рассылка подписчикам"),
            BotCommand("admin", "⚙ Админ-панель"),
            BotCommand("log", "📜 Лог пользователя"),
        ],
        scope=BotCommandScopeChat(chat_id=Config.ADMIN_CHAT_ID)
    )

# Точка входа
async def main():
    init_db()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    await setup_bot_commands(app)  # ← устанавливаем меню

    start_scheduler(app.bot)       # ← запускаем планировщик

    # обработчики
    app.add_handler(get_start_handler())
    app.add_handler(get_button_handler())

    for handler in get_admin_handlers():
        app.add_handler(handler)

    await app.run_polling(close_loop=False)


   # Запускаем
if __name__ == "__main__":
    asyncio.run(main())