import logging
from aiohttp import web
from telegram import Update, BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config import config
from db import init_db, create_indexes, get_all_admins
from handlers.start import start
from handlers.admin import get_admin_handlers
from handlers.user_buttons import get_user_button_handler
from handlers.admin_buttons import (
    get_admin_button_handler,
    message_user_callback,
    send_text_to_user
)
from handlers.text_buttons import handle_text_buttons
from handlers.payments import setup_payment_handlers
from handlers.update_payment import (
    handle_update_pay_command,
    handle_name_input,
    handle_user_selected,
    handle_channel_selected,
    handle_date_input,
)
from utils.scheduler import start_scheduler
from utils.pagination import handle_pagination_callback
from logger import setup_logging

# Инициализация логирования
setup_logging()
logger = logging.getLogger(__name__)

async def create_telegram_app():
    """Создание и инициализация Telegram приложения"""
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    await app.initialize()
    await app.start()
    return app

async def on_startup(app: web.Application):
    """Инициализация при запуске"""
    try:
        logger.info("Starting application initialization...")

        # 1. Инициализация БД
        init_db()
        create_indexes()
        logger.info("Database initialized")

        # 2. Создание Telegram приложения
        telegram_app = await create_telegram_app()
        app['telegram_app'] = telegram_app
        logger.info("Telegram app started")

        # 3. Очистка обновлений
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted")

        # 4. Настройка платежей
        setup_payment_handlers(telegram_app)
        logger.info("Payment handlers configured")

        # 5. Запуск планировщика
        start_scheduler(telegram_app.bot)
        logger.info("Scheduler started")

        # 6. Настройка команд бота
        await setup_bot_commands(telegram_app)
        logger.info("Bot commands configured")

        # 7. Регистрация обработчиков
        setup_handlers(telegram_app)
        logger.info("Handlers registered")

        # 8. Настройка вебхука
        webhook_url = f"https://{config.WEBHOOK_HOST}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook configured at {webhook_url}")

    except Exception as e:
        logger.critical(f"Application startup failed: {e}")
        raise

async def on_shutdown(app: web.Application):
    """Очистка при завершении"""
    logger.info("Shutting down application...")
    try:
        telegram_app = app.get('telegram_app')
        if telegram_app:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram app stopped gracefully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

async def setup_bot_commands(app):
    """Настройка команд бота"""
    # Основные команды
    await app.bot.set_my_commands(
        [BotCommand("start", "Запустить бота")],
        scope=BotCommandScopeDefault()
    )

    # Команды для админов
    admin_commands = [
        BotCommand("admin", "⚙ Админ-панель"),
        BotCommand("invite", "📩 Приглашение в канал"),
        BotCommand("update_pay", "📝 Внести дату оплаты вручную"),
        BotCommand("broadcast", "📢 Рассылка подписчикам"),
        BotCommand("start", "Запустить бота"),
    ]

    for admin in get_all_admins():
        try:
            await app.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin[0])
            )
        except Exception as e:
            logger.error(f"Failed to set commands for admin {admin[0]}: {e}")


def setup_handlers(app):
    """Регистрация обработчиков"""
    # Обработчики колбэков
    app.add_handler(CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"))
    app.add_handler(CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"))
    app.add_handler(CallbackQueryHandler(handle_pagination_callback,
                                         pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"))
    app.add_handler(CallbackQueryHandler(message_user_callback, pattern=r"^message_user:\d+$"))

    # Командные обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update_pay", handle_update_pay_command))

    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_text_to_user))



    # Добавляем admin handlers
    for handler in get_admin_handlers():
        app.add_handler(handler)

    app.add_handler(get_admin_button_handler())
    app.add_handler(get_user_button_handler())

async def webhook_handler(request: web.Request):
    """Обработчик вебхука"""
    try:
        telegram_app = request.app['telegram_app']
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=400)


def init_app():
    """Инициализация AioHTTP приложения"""
    app = web.Application()

    # Управление жизненным циклом
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Роутинг
    app.router.add_post('/webhook', webhook_handler)

    return app


if __name__ == '__main__':
    app = init_app()
    web.run_app(
        app,
        host='127.0.0.1',  # Должен совпадать с proxy_pass в Nginx
        port=8000,  # Должен совпадать с proxy_pass в Nginx
    )
