from telegram.ext import ContextTypes, CommandHandler
from db import get_unpaid_users
from keyboards.main import build_user_confirm_button
from utils.storage import save_invite_message_id
from db import get_all_users
from utils.storage import load_invite_message_id
from keyboards.main import build_history_keyboard, build_admin_panel
from utils.formatting import format_user_card
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from db import save_invite_message_id  # если используется

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    bot_username = context.bot.username
    success_channels = []

    for key, channel in Config.CHANNELS.items():
        start_link = f"https://t.me/{bot_username}?start={key}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Подписаться на бота", url=start_link)]
        ])

        text = (
            f"🏊‍♂️ Привет, друзья!\n"
            f"Вы находитесь в канале <b>{channel['title']}</b>\n\n"
            "Чтобы не пропустить оплату за тренировку — подпишитесь на нашего бота 📩\n\n"
            "Он будет мягко и вовремя напоминать вам об оплате 💳"
        )

        try:
            msg = await context.bot.send_message(
                chat_id=channel["id"],
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            # Сохраняем ID приглашения, если нужно
            # save_invite_message_id(key, msg.message_id)
            success_channels.append(channel["title"])
        except Exception as e:
            print(f"❌ Не удалось отправить сообщение в канал {channel['title']}: {e}")

    if success_channels:
        await update.message.reply_text(f"✅ Приглашение отправлено в:\n" + "\n".join(success_channels))
    else:
        await update.message.reply_text("⚠️ Не удалось отправить ни одного приглашения.")


        # Сохраняем message_id для команды /pin_invite
        save_invite_message_id(key, msg.message_id)

    await update.message.reply_text("✅ Приглашения успешно отправлены во все каналы!")


async def pin_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    msg_id = load_invite_message_id()
    if not msg_id:
        await update.message.reply_text("⚠️ Нет сохранённого приглашения. Сначала вызови /invite.")
        return

    await context.bot.pin_chat_message(chat_id=Config.CHANNEL_ID, message_id=msg_id)
    await update.message.reply_text("📌 Сообщение закреплено в канале.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
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
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
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
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
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
PAGE_SIZE = 10  # количество карточек на одной странице

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.callback_query.message

    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
        await message.reply_text("⛔ Только для администратора.")
        return

    # Получаем параметры
    query = " ".join(context.args).lower() if context.args else ""
    users = get_all_users()

    # Фильтрация
    filters = query.split()
    search_term = None
    status_filter = None
    sort_latest = False
    channel_filter = None

    for f in filters:
        if f.startswith("only="):
            status_filter = f.split("=")[1]
        elif f.startswith("sort=") and f.split("=")[1] == "latest":
            sort_latest = True
        elif f.startswith("channel="):
            channel_filter = f.split("=")[1]
        else:
            search_term = f

    if search_term:
        users = [u for u in users if search_term in (u[1].lower() + " " + str(u[0]))]
    if status_filter:
        users = [u for u in users if u[2] == status_filter]
    if channel_filter:
        users = [u for u in users if u[5] == channel_filter]
    if sort_latest:
        users.sort(key=lambda x: x[3] or "", reverse=True)
    else:
        users.sort(key=lambda x: x[1])

    if not users:
        await message.reply_text("⚠️ Подходящих пользователей не найдено.")
        return

    # Сохраняем state
    context.user_data["history_state"] = {
        "users": users,
        "page": 0,
        "query": query,
    }

    await send_history_page(message, context)

    # --- Вывод заголовка, если фильтруем по каналу ---
    if channel_filter:
        channel_info = Config.CHANNELS.get(channel_filter)
        title = channel_info["title"] if channel_info else channel_filter.capitalize()
        await message.reply_text(f"📋 Пользователи канала <b>{title}</b> ({len(users)} чел.)", parse_mode="HTML")
    elif query:
        await message.reply_text(f"📋 Найдено пользователей: <b>{len(users)}</b>", parse_mode="HTML")

    # --- Вывод карточек пользователей ---
    for user in users:
        user_id, name, status, payment_date, previous_date, channel_key, username = user

        # Получаем username, если возможно
        try:
            tg_user = await context.bot.get_chat(user_id)
            username = tg_user.username
        except:
            username = None

        text = format_user_card(
            user_id=user_id,
            name=name,
            status=status,
            payment_date=payment_date,
            previous_date=previous_date,
            channel_key=channel_key,
            username=username
        )

        await message.reply_text(
            text=text,
            reply_markup=build_history_keyboard(user_id, status),
            parse_mode="HTML"
        )
async def send_history_page(message, context):
    state = context.user_data.get("history_state")
    if not state:
        await message.reply_text("⚠️ Данные не найдены.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await message.reply_text("📭 Нет данных для этой страницы.")
        return

    total_pages = (len(users) - 1) // PAGE_SIZE + 1

    for user in page_users:
        user_id, name, status, payment_date, previous_date, channel_key, username = user
        try:
            tg_user = await context.bot.get_chat(user_id)
            username = tg_user.username or username
        except:
            pass

        text = format_user_card(
            user_id=user_id,
            name=name,
            status=status,
            payment_date=payment_date,
            previous_date=previous_date,
            channel_key=channel_key,
            username=username
        )

        await message.reply_text(
            text=text,
            reply_markup=build_history_keyboard(user_id, status),
            parse_mode="HTML"
        )

    # Кнопки листания
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅ Назад", callback_data="history_page:prev"))
    if end < len(users):
        buttons.append(InlineKeyboardButton("Вперёд ➡", callback_data="history_page:next"))

    if buttons:
        await message.reply_text(
            f"📄 Страница {page + 1} из {total_pages}",
            reply_markup=InlineKeyboardMarkup([buttons])
        )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
        await update.message.reply_text("⛔ Только для администратора.")
        return

    await update.message.reply_text("🛠 Панель администратора", reply_markup=build_admin_panel())

from db import get_user_payment_log

async def user_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
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

async def update_pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in Config.ADMIN_CHAT_IDS:
        return await update.message.reply_text("⛔ Только для администратора.")

    await update.message.reply_text(
        "📝 Введите имя или username пользователя, которому нужно изменить дату последней оплаты:"
    )
    return ConversationHandler.WAITING_FOR_NAME


def get_admin_handlers():
    return [
        CommandHandler("list_unpaid", list_unpaid),
        CommandHandler("invite", invite),
        CommandHandler("pin_invite", pin_invite),
        CommandHandler("broadcastbroadcast", broadcast),
        CommandHandler("list_paid", list_paid),
        CommandHandler("history", history),
        CommandHandler("admin", admin_panel),
    ]