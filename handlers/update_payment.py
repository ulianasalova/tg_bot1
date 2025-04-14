from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_all_users, update_payment_date
import re

SELECTED_USER_ID = "selected_user_id"
AWAITING_DATE = "awaiting_date"

# Шаг 1 — старт команды
async def handle_update_pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Введите имя, ID или username пользователя:")
    context.user_data.clear()

# Шаг 2 — обработка ввода имени
async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(AWAITING_DATE):
        return await handle_date_input(update, context)

    query = update.message.text.strip().lower()
    users = get_all_users()

    matched = []
    for user_id, name, *_ in users:
        name_lower = name.lower()
        if query in name_lower or query in str(user_id):
            matched.append((user_id, name))

    if not matched:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
        return

    keyboard = [
        [InlineKeyboardButton(f"{name} (ID: {user_id})", callback_data=f"select_user:{user_id}")]
        for user_id, name in matched
    ]

    await update.message.reply_text("👤 Выберите пользователя:", reply_markup=InlineKeyboardMarkup(keyboard))

# Шаг 3 — выбор пользователя кнопкой
async def handle_user_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split(":")[1])
    context.user_data[SELECTED_USER_ID] = user_id
    context.user_data[AWAITING_DATE] = True

    await query.message.reply_text("📅 Введите дату оплаты в формате ГГГГ-ММ-ДД (например, 2025-04-01):")

# Шаг 4 — ввод даты
async def handle_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get(SELECTED_USER_ID)
    if not user_id:
        await update.message.reply_text("❌ Пользователь не выбран. Сначала выполните команду /update_pay")
        return

    date = update.message.text.strip()
    if not re.match(r"\d{4}-\d{2}-\d{2}$", date):
        await update.message.reply_text("❌ Неверный формат. Введите в виде ГГГГ-ММ-ДД:")
        return

    try:
        update_payment_date(user_id, date)
        await update.message.reply_text(f"✅ Дата оплаты пользователя {user_id} обновлена на {date}")
    except Exception as e:
        await update.message.reply_text(f"⚠ Ошибка при обновлении даты: {e}")

    context.user_data.clear()
