from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db import get_unpaid_users
from keyboards.main import build_user_confirm_button
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config
from utils.storage import save_invite_message_id
from db import get_all_users
from utils.storage import load_invite_message_id
from keyboards.main import build_history_keyboard
from keyboards.main import build_admin_panel

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    bot_link = f"https://t.me/{context.bot.username}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Подписаться на бота", url=bot_link)]
    ])

    msg = await context.bot.send_message(
        chat_id=Config.CHANNEL_ID,
        text=(
            "🏊‍♂️ Привет, друзья!\n"
            "Чтобы не пропустить оплату за тренировку — подпишитесь на нашего бота 📩\n\n"
            "Он будет мягко и вовремя напоминать вам об оплате 💳"
        ),
        reply_markup=keyboard
    )

    save_invite_message_id(msg.message_id)

    await update.message.reply_text("✅ Приглашение отправлено в канал!")

async def pin_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    msg_id = load_invite_message_id()
    if not msg_id:
        await update.message.reply_text("⚠️ Нет сохранённого приглашения. Сначала вызови /invite.")
        return

    await context.bot.pin_chat_message(chat_id=Config.CHANNEL_ID, message_id=msg_id)
    await update.message.reply_text("📌 Сообщение закреплено в канале.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    if not context.args:
        await update.message.reply_text("📩 Использование: /broadcast ТЕКСТ_СООБЩЕНИЯ")
        return

    message = " ".join(context.args)
    users = get_all_users()
    count = 0

    for user in users:
        user_id = user[0]
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            print(f"⚠️ Не доставлено {user_id}: {e}")

    await update.message.reply_text(f"✅ Сообщение отправлено {count} пользователям.")

async def list_unpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Команда только для администратора")
        return

    users = get_unpaid_users()
    if not users:
        await update.message.reply_text("🎉 Все пользователи оплатили.")
        return

    for user_id, name in users:
        await update.message.reply_text(
            text=f"👤 {name} (ID: {user_id})",
            reply_markup=build_user_confirm_button(user_id)
        )

from utils.scheduler import send_reminders  # не забудь импортировать

from db import get_unpaid_users

from db import get_all_users
from keyboards.main import build_user_cancel_button

async def list_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    users = get_all_users()
    paid_users = [u for u in users if u[2] == "paid"]

    if not paid_users:
        await update.message.reply_text("❗ Оплаченных пользователей пока нет.")
        return

    for user in paid_users:
        user_id, name, status, payment_date, previous_payment_date, next_reminder_date = user
        try:
            user_chat = await context.bot.get_chat(user_id)
            username = f"@{user_chat.username}" if user_chat.username else "(без username)"
        except:
            username = "(недоступен)"

        await update.message.reply_text(
            text=f"👤 {name} {username}\n📅 Оплата: {payment_date}",
            reply_markup=build_user_cancel_button(user_id)
        )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        message = update.message or update.callback_query.message
        await message.reply_text("⛔ Только для администратора.")
        return

    query = " ".join(context.args).lower() if context.args else ""

    users = get_all_users()

    # Фильтрация и сортировка
    if query:
        filters = query.split()
        search_term = None
        status_filter = None
        sort_latest = False

        for f in filters:
            if f.startswith("only="):
                status_filter = f.split("=")[1]
            elif f.startswith("sort=") and f.split("=")[1] == "latest":
                sort_latest = True
            else:
                search_term = f

        if search_term:
            users = [
                u for u in users if search_term in (u[1].lower() + " " + str(u[0]))
            ]

        if status_filter:
            users = [u for u in users if u[2] == status_filter]

        if sort_latest:
            users.sort(key=lambda x: x[3] or "", reverse=True)  # по дате оплаты
    else:
        users.sort(key=lambda x: x[1])  # по имени

    message = update.message or update.callback_query.message

    if not users:
        await message.reply_text("⚠️ Подходящих пользователей не найдено.")
        return

    for user in users:
        user_id, name, status, payment_date, previous_payment_date, next_reminder_date = user

        try:
            tg_user = await context.bot.get_chat(user_id)
            username = f"@{tg_user.username}" if tg_user.username else "(без username)"
        except:
            username = "(недоступен)"

        status_text = "✅ Оплачено" if status == "paid" else "❌ Не оплачено"
        date_text = f"📅 Оплата: {payment_date}" if payment_date else "📅 Оплата: —"

        await message.reply_text(
            text=(
                f"👤 {name} {username}\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"{date_text}\n"
                f"💳 Статус: {status_text}"
            ),
            parse_mode="HTML",
            reply_markup=build_history_keyboard(user_id, status)
        )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    await update.message.reply_text("🛠 Панель администратора", reply_markup=build_admin_panel())

from db import get_user_payment_log

async def user_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != Config.ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    if not context.args:
        await update.message.reply_text("❗ Использование: /log <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ user_id должен быть числом.")
        return

    logs = get_user_payment_log(user_id)

    if not logs:
        await update.message.reply_text("ℹ️ История для этого пользователя пуста.")
        return

    text = f"📜 История пользователя {user_id}:\n\n"
    for log in logs:
        date_logged, action, old_date, new_date, by_admin = log

        if action == "confirmed":
            text += f"🟢 {date_logged[:10]} — подтверждена оплата (новая: {new_date})\n"
        elif action == "cancelled":
            text += f"🔴 {date_logged[:10]} — отмена оплаты (старая: {old_date})\n"
        else:
            text += f"⚙️ {date_logged[:10]} — действие: {action}\n"

    await update.message.reply_text(text)


def get_admin_handlers():
    return [
        CommandHandler("list_unpaid", list_unpaid),
        CommandHandler("invite", invite),
        CommandHandler("pin_invite", pin_invite),
        CommandHandler("broadcast", broadcast),
        CommandHandler("list_paid", list_paid),
        CommandHandler("history", history),
        CommandHandler("admin", admin_panel),
        CommandHandler("log", user_log),
    ]