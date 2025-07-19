from telegram import Update, LabeledPrice
from datetime import datetime, timedelta
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters
)
from db import mark_as_paid_custom
from config import config
import logging

logger = logging.getLogger(__name__)


async def handle_payment_button(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        await query.answer()

        # Создаем fake update с message для совместимости
        fake_update = Update(
            update.update_id,
            message=query.message,
            callback_query=query
        )

        await buy_subscription(fake_update, context)

    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопки оплаты: {e}")
        await query.message.reply_text("❌ Ошибка при обработке запроса")
def setup_payment_handlers(app: Application):
    app.add_handler(CommandHandler("buy", buy_subscription))
    app.add_handler(PreCheckoutQueryHandler(process_pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, process_successful_payment))
    app.add_handler(CallbackQueryHandler(handle_payment_button, pattern="^buy_subscription$"))

async def buy_subscription(update: Update, context: CallbackContext):
    try:

        # Получаем message из update (работает и для команд, и для кнопок)
        message = update.message or update.callback_query.message
        # if config.PROVIDER_TOKEN.split(':')[1] == 'TEST':
        #     await update.message.reply_text(
        #         "Для оплаты используйте данные тестовой карты:\n"
        #         "1111 1111 1111 1026, 12/22, CVC 000."
        #     )

        prices = [LabeledPrice(label='Оплата заказа', amount=config.PRICE)]

        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title='Покупка подписки',
            description='Доступ к каналу на 1 месяц',
            payload='bot_paid',
            provider_token=config.PROVIDER_TOKEN,
            currency=config.CURRENCY,
            prices=prices,
            need_phone_number=True,
            send_phone_number_to_provider=True,
            provider_data=config.provider_data
        )

    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /buy: {e}")
        await update.message.reply_text("Произошла ошибка при обработке команды!")

async def process_pre_checkout_query(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    try:
        await query.answer(ok=True)  # Подтверждаем предварительный запрос
    except Exception as e:
        logger.error(f"Ошибка при обработке pre-checkout: {e}")


async def process_successful_payment(update: Update, context: CallbackContext):
    payment = update.message.successful_payment
    try:
        user_id = update.effective_user.id

        # 1. Получаем channel_key из payload (если передавали при создании инвойса)
        channel_key = "swimmasters"  # Замените на ваш ключ канала или получите из payload

        # 2. Формируем дату платежа
        payment_date = datetime.now().date()  # Или используйте дату из платежной системы

        # 3. Вызываем функцию обновления БД
        mark_as_paid_custom(
            user_id=user_id,
            channel_key=channel_key,
            payment_date=payment_date,
            action='confirmed'  # Или None, если не нужно логировать действие
        )

        # 4. Отправляем подтверждение пользователю
        await update.message.reply_text(
            f"✅ Платеж на сумму {payment.total_amount // 100} {payment.currency} принят!\n"
            f"Доступ к каналу активирован до {payment_date + timedelta(days=30):%d.%m.%Y}"
        )

        logger.info(f"Успешный платеж: user_id={user_id}, channel={channel_key}, sum={payment.total_amount}")

    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await update.message.reply_text("⚠ Ошибка активации доступа. Администратор уведомлен.")

