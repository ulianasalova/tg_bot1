import asyncio
import nest_asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from config import Config
from db import init_db, create_indexes, get_all_admins
from handlers.start import start
from handlers.admin import get_admin_handlers
from handlers.user_buttons import get_user_button_handler
from handlers.admin_buttons import get_admin_button_handler
from handlers.text_buttons import handle_text_buttons
from handlers.update_payment import (
    handle_update_pay_command,
    handle_name_input,
    handle_user_selected,
    handle_channel_selected,
    handle_date_input,
)
from utils.scheduler import start_scheduler
from utils.pagination import handle_pagination_callback

nest_asyncio.apply()

async def setup_bot_commands(app):
    await app.bot.set_my_commands(
        [BotCommand("start", "Запустить бота")],
        scope=BotCommandScopeDefault()
    )

    admin_commands = [
        BotCommand("admin", "⚙ Админ-панель"),
        BotCommand("invite", "📩 Приглашение в канал"),
        BotCommand("update_pay", "📝 Внести дату оплаты вручную"),
        BotCommand("broadcast", "📢 Рассылка подписчикам"),
        BotCommand("start", "Запустить бота"),
    ]

    admins = get_all_admins()
    for admin in admins:
        admin_id = admin[0]
        await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))

async def main():
    init_db()
    create_indexes()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    await setup_bot_commands(app)
    start_scheduler(app.bot)

    # --- Обработчики ---
    app.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
    app.add_handler(CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"))
    app.add_handler(CallbackQueryHandler(handle_pagination_callback, pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"))
    app.add_handler(get_admin_button_handler())
    app.add_handler(get_user_button_handler())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update_pay", handle_update_pay_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

    # ВЕЧНЫЙ ЦИКЛ для удержания процесса
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
