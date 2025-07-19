import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
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

def create_telegram_app():
    """Фабрика для создания Telegram приложения"""
    return ApplicationBuilder().token(config.BOT_TOKEN).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    telegram_app = create_telegram_app()
    
    try:
        # --- STARTUP ---
        logger.info("Starting application initialization...")
        
        # 1. Инициализация базы данных
        init_db()
        create_indexes()
        logger.info("Database initialized")

        # 2. Запуск Telegram бота
        await telegram_app.initialize()
        await telegram_app.start()
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
        await setup_webhook(telegram_app)
        logger.info("Webhook configured")

        # Сохраняем приложение в состоянии FastAPI
        app.state.telegram_app = telegram_app

        yield

    except Exception as e:
        logger.critical(f"Application startup failed: {e}")
        raise

    finally:
        # --- SHUTDOWN ---
        logger.info("Shutting down application...")
        try:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram app stopped gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def setup_bot_commands(app):
    """Настройка команд бота для пользователей и админов"""
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
    """Регистрация всех обработчиков"""
    # Обработчики колбэков
    app.add_handlers([
        CallbackQueryHandler(handle_user_selected, pattern=r"^select_user:"),
        CallbackQueryHandler(handle_channel_selected, pattern=r"^select_channel:"),
        CallbackQueryHandler(handle_pagination_callback, pattern=r"^(paid_page|unpaid_page|history_page):(prev|next)$"),
        CallbackQueryHandler(message_user_callback, pattern=r"^message_user:\d+$")
    ])

    # Обработчики сообщений
    app.add_handlers([
        MessageHandler(filters.TEXT & ~filters.COMMAND, send_text_to_user),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons)
    ])

    # Командные обработчики
    app.add_handlers([
        CommandHandler("start", start),
        CommandHandler("update_pay", handle_update_pay_command),
        *get_admin_handlers(),
        get_admin_button_handler(),
        get_user_button_handler()
    ])

async def setup_webhook(app):
    """Настройка вебхука"""
    webhook_url = f"https://{config.WEBHOOK_HOST}/webhook"
    await app.bot.set_webhook(url=webhook_url)

# Создание FastAPI приложения
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Обработчик вебхука от Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, bot=app.state.telegram_app.bot)
        await app.state.telegram_app.process_update(update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
