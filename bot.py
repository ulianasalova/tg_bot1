import asyncio
import nest_asyncio
from fastapi import FastAPI, Request
from telegram import Update, BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from contextlib import asynccontextmanager

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

# Создаем FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    create_indexes()

    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_commands()

    start_scheduler(telegram_app.bot)

    webhook_url = f"https://{Config.WEBHOOK_HOST}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url)
    print("\u2705 Lifespan startup complete")
    yield
    print("\u23F9 Lifespan shutdown")

app = FastAPI(lifespan=lifespan)

# Настроим Telegram приложение
telegram_app: Application = ApplicationBuilder().token(Config.BOT_TOKEN).build()

async def setup_bot_commands():
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
    ], scope=BotCommandScopeDefault())

    admin_commands = [
        BotCommand("admin", "⚙ Админ-панель"),
        BotCommand("invite", "📩 Приглашение в канал"),
        BotCommand("update_pay", "📝 Внести дату оплаты вручную"),
        BotCommand("broadcast", "📢 Рассылка подписчикам"),
        BotCommand("start", "Запустить бота"),
    ]

    admins = get_all_admins()
    for admin in admins:
        await telegram_app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin[0]))

# Вебхук обработчик
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot=telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# Регистрируем хендлеры
telegram_app.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
telegram_app.add_handler(CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"))
telegram_app.add_handler(CallbackQueryHandler(handle_pagination_callback, pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"))
telegram_app.add_handler(get_admin_button_handler())
telegram_app.add_handler(get_user_button_handler())
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("update_pay", handle_update_pay_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
for handler in get_admin_handlers():
    telegram_app.add_handler(handler)
