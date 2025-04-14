import asyncio
import nest_asyncio
nest_asyncio.apply()
from telegram.ext import ApplicationBuilder
from config import Config
from db import init_db
from handlers.start import get_start_handler
from handlers.admin import get_admin_handlers
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from utils.scheduler import start_scheduler, send_reminders
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from handlers.update_payment import (
    handle_update_pay_command,
    handle_user_selected,
    handle_name_input,
    handle_date_input
)
from handlers.buttons import get_user_button_handler, get_admin_button_handler
from handlers.buttons import handle_text_buttons


# Устанавливаем команды
async def setup_bot_commands(app):
    # Команды для всех пользователей
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
        ],
        scope=BotCommandScopeDefault()
    )

    # Команды для админов
    admin_commands = [
        BotCommand("admin", "⚙ Админ-панель"),
        BotCommand("invite", "📩 Приглашение в канал"),
        BotCommand("pin_invite", "📌 Закрепить приглашение"),
        BotCommand("update_pay", "📝 Внести дату оплаты вручную"),
        BotCommand("broadcast", "📢 Рассылка подписчикам"),
        BotCommand("start", "Запустить бота"),

    ]

    for admin_id in Config.ADMIN_CHAT_IDS:
        await app.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_id)
        )
# Точка входа
async def main():
    init_db()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    await app.bot.delete_webhook(drop_pending_updates=True)  # ⬅️ Добавляем эту строку

    await setup_bot_commands(app)
    start_scheduler(app.bot)

    app.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
    app.add_handler(get_start_handler())
    app.add_handler(get_admin_button_handler())  # кнопки для админки
    app.add_handler(get_user_button_handler())  # кнопки от обычных пользователей

    app.add_handler(CommandHandler("update_pay", handle_update_pay_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

    for handler in get_admin_handlers():
        app.add_handler(handler)

    await app.run_polling(close_loop=False)  # ✅ await добавлен


   # Запускаем
if __name__ == "__main__":
    asyncio.run(main())
    