import asyncio
import nest_asyncio
from fastapi import FastAPI, Request
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

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

app = FastAPI()

application = ApplicationBuilder().token(Config.BOT_TOKEN).build()

# Устанавливаем команды
async def setup_bot_commands():
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
        ],
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
        await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))

# Роут для вебхуков
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot=application.bot)
    await application.initialize()
    await application.process_update(update)
    return {"ok": True}

async def main():
    init_db()
    create_indexes()

    await application.bot.delete_webhook(drop_pending_updates=True)
    await setup_bot_commands()
    start_scheduler(application.bot)
    import asyncio

    async def main():
        init_db()
        create_indexes()

        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

        await setup_bot_commands(app)
        start_scheduler(app.bot)

        # Теперь вечная "спящая" задача
        while True:
            await asyncio.sleep(3600)

    # --- Обработчики ---

    application.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
    application.add_handler(CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"))
    application.add_handler(CallbackQueryHandler(handle_pagination_callback, pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"))

    application.add_handler(get_admin_button_handler())  # 💥 ВЕРХ
    application.add_handler(get_user_button_handler())
    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("update_pay", handle_update_pay_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))

    for handler in get_admin_handlers():
        application.add_handler(handler)




if __name__ == "__main__":
    asyncio.run(main())

