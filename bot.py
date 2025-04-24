import asyncio
import nest_asyncio
from telegram.ext import ApplicationBuilder
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from config import Config
from db import init_db, create_indexes, get_all_admins
from handlers.start import start
from handlers.admin import get_admin_handlers
# Пользовательские кнопки (inline)
from handlers.user_buttons import get_user_button_handler
# Админские кнопки (inline)
from handlers.admin_buttons import get_admin_button_handler
# Текстовые кнопки (menu)
from handlers.text_buttons import handle_text_buttons
# Обновление даты оплаты
from handlers.update_payment import (
    handle_update_pay_command,
    handle_name_input,
    handle_user_selected,
    handle_channel_selected,
    handle_date_input,
)
from utils.scheduler import start_scheduler
from utils.pagination import handle_pagination_callback
from telegram.ext import  CommandHandler, MessageHandler, CallbackQueryHandler, filters

nest_asyncio.apply()


# Устанавливаем команды
async def setup_bot_commands(app):
    # Команды для всех пользователей
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
        ],
        scope=BotCommandScopeDefault()
    )

    # Команды для админов из таблицы admins
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
from handlers.admin import update_pay_command



# Основная точка входа
async def main():
    init_db()
    create_indexes()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    await app.bot.delete_webhook(drop_pending_updates=True)

    await setup_bot_commands(app)
    start_scheduler(app.bot)

        # --- Обработчики ---

    app.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
    app.add_handler(CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"))
    app.add_handler(CallbackQueryHandler(handle_pagination_callback, pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"))

    app.add_handler(get_admin_button_handler())  # 💥 ВЕРХ!
    app.add_handler(get_user_button_handler())
    app.add_handler(CommandHandler("start", start))
        # Обновление оплаты вручную
    app.add_handler(CommandHandler("update_pay", handle_update_pay_command))
     # Ввод имени и даты
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))


    # Дополнительные админ-команды (например, /broadcast и т.д.)
    for handler in get_admin_handlers():
        app.add_handler(handler)

    app.run_polling(close_loop=False)

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
