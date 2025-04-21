from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from keyboards.main import build_channel_keyboard
from db import get_user_by_id, get_user_channels
from datetime import datetime, timedelta


async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "ℹ️ Информация о каналах":
        text = "\n\n".join([
            f"<b>{c['title']}</b>\n{c['description']}"
            for c in Config.CHANNELS.values()
        ])
        await update.message.reply_text(text, parse_mode="HTML")

    elif text == "💳 Оплата":
        await update.message.reply_text(
            "💳 Чтобы получить реквизиты для оплаты, нажмите кнопку «✅ Я оплатил» после выбора канала."
        )

    elif text == "📄 Моя подписка":
        user_data = get_user_by_id(user_id)

        if not user_data:
            await update.message.reply_text("🚫 Вы пока не зарегистрированы.")
            return

        name = user_data[1]
        channels = get_user_channels(user_id)

        if not channels:
            await update.message.reply_text("📭 У вас нет активных подписок.")
            return

        message_lines = [f"📄 <b>Подписки пользователя {name}</b> (ID: <code>{user_id}</code>):\n"]

        for ch in channels:
            channel_key = ch["channel_key"]
            payment_date = ch["payment_date"]
            previous_date = ch["previous_payment_date"]

            channel_info = Config.CHANNELS.get(channel_key)
            channel_title = channel_info["title"] if channel_info else channel_key

            if payment_date:
                try:
                    pay_date = datetime.strptime(payment_date, "%Y-%m-%d")
                    next_due = pay_date + timedelta(days=30)
                    today = datetime.now().date()
                    days_left = (next_due.date() - today).days

                    if days_left < 0:
                        pay_status = f"⛔ Срок истёк {abs(days_left)} дн. назад"
                    elif days_left == 0:
                        pay_status = "⚠️ Оплата сегодня!"
                    else:
                        pay_status = f"⏳ Осталось {days_left} дн."
                except:
                    pay_status = "⚠️ Ошибка в дате"
            else:
                pay_status = "❌ Не оплачено"

            line = (
                f"\n<b>{channel_title}</b>\n"
                f"📅 Последняя оплата: {payment_date or '—'}\n"
                f"{pay_status}"
            )
            message_lines.append(line)

        text = "\n".join(message_lines)
        await update.message.reply_text(text, parse_mode="HTML")

    elif text == "🧾 Выбрать канал":
        await update.message.reply_text(
            "Выберите канал для подписки:",
            reply_markup=build_channel_keyboard()
        )

    elif text == "📩 Написать админу":
        await update.message.reply_text("📩 Связь с админом: @ulianasalova")
