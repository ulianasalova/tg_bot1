from telegram.ext import ContextTypes, CommandHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from utils.pagination import send_paid_users_page, send_unpaid_users_page
from db import get_paid_users_for_admin
from telegram import Update
from telegram.ext import ContextTypes
from db import get_unpaid_users_with_channels, is_admin
from utils.storage import fetch_channels


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return

    bot_username = context.bot.username
    success_channels = []

    for key, channel in fetch_channels().items():
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

            # Пытаемся закрепить сообщение
            try:
                await context.bot.pin_chat_message(chat_id=channel["id"], message_id=msg.message_id)
            except Exception as pin_err:
                print(f"⚠️ Не удалось закрепить сообщение в {channel['title']}: {pin_err}")

            success_channels.append(channel["title"])

        except Exception as e:
            print(f"❌ Не удалось отправить сообщение в канал {channel['title']}: {e}")

    if success_channels:
        await update.message.reply_text(f"✅ Приглашение отправлено и закреплено в:\n" + "\n".join(success_channels))
    else:
        await update.message.reply_text("⚠️ Не удалось отправить ни одного приглашения.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        await update.message.reply_text("⛔ Только для администратора.")
        return

    if not context.args:
        await update.message.reply_text("📩 Использование: /broadcast ТЕКСТ_СООБЩЕНИЯ")
        return

    message = " ".join(context.args)

    # Получаем список каналов, за которые отвечает админ
    from db import get_admin_channels
    admin_channels = get_admin_channels(admin_id)

    # Получаем пользователей этих каналов
    from db import get_users_by_channels
    users = get_users_by_channels(admin_channels)

    count = 0
    for user_id, name in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            print(f"⚠️ Не доставлено {user_id}: {e}")

    await update.message.reply_text(f"✅ Сообщение отправлено {count} пользователям.")


async def list_unpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Команда только для администратора")
        return

    raw_users = get_unpaid_users_with_channels()

    if not raw_users:
        await update.message.reply_text("🎉 Все пользователи оплатили.")
        return

    # (user_id, name, channel_key) → теперь добавим username для вывода карточек
    # users = []
    # for user_id, name, status, channel_key, payment_date in raw_users:
    #     try:
    #         chat = await context.bot.get_chat(user_id)
    #         username = chat.username
    #     except:
    #         username = None
    #     users.append((user_id, name, status, username, channel_key, payment_date))

    # сохраняем в context
    context.user_data["unpaid_list"] = {
        "users": users,
        "page": 0,
    }

    await send_unpaid_users_page(update.message, context)


async def list_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        await update.message.reply_text("⛔ Только для администратора.")
        return

    # Получаем пользователей с оплатой
    paid_users = get_paid_users_for_admin(admin_id)

    if not paid_users:
        await update.message.reply_text("❗ Оплаченных пользователей пока нет.")
        return

    # Сохраняем состояние в user_data
    context.user_data["paid_list"] = {
        "users": paid_users,
        "page": 0
    }

    # Показываем первую страницу
    await send_paid_users_page(update.message, context)

from utils.formatting import format_user_card
from utils.pagination import build_pagination_keyboard
from keyboards.main import build_history_keyboard

PAGE_SIZE = 10

async def send_history_page(message, context):
    state = context.user_data.get("history_state")
    if not state:
        await message.reply_text("❌ Нет данных для отображения.")
        return

    page = state["page"]
    users = state["users"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current_users = users[start:end]

    if not current_users:
        await message.reply_text("⚠️ Нет данных на этой странице.")
        return

    for user in current_users:
        user_id = user["user_id"]
        name = user["name"]
        status = user["payment_status"]
        payment_date = user["payment_date"]
        previous_date = user.get("previous_date")  # может быть None
        channel_key = user["channel_key"]
        username = user.get("username")  # может быть None

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
            reply_markup=build_history_keyboard(user_id, status, channel_key, payment_date),
            parse_mode="HTML"
        )

    # ➕ Пагинация
    keyboard = build_pagination_keyboard(
        page=page,
        total=len(users),
        prefix="history_page",
        page_size=PAGE_SIZE
    )

    if keyboard:
        await message.reply_text("📄 Навигация по страницам:", reply_markup=keyboard)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db import get_all_users_with_channels
    message = update.message or update.callback_query.message

    if not is_admin(update.effective_user.id):
        await message.reply_text("⛔ Только для администратора.")
        return

    query = " ".join(context.args).lower() if context.args else ""
    users = get_all_users_with_channels()

    # --- Фильтрация ---
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

    # 🔍 Поиск по имени/ID
    if search_term:
        users = [
            u for u in users
            if search_term in (u["name"].lower() + " " + str(u["user_id"]))
        ]

    # 🎯 Специальная фильтрация по статусу
    if status_filter == "new_users":
        users = [
            u for u in users
            if u["payment_status"] == "not_paid" and u["payment_date"] is None
        ]
    elif status_filter:
        users = [u for u in users if u["payment_status"] == status_filter]

    # 🎯 Фильтр по каналу
    if channel_filter:
        users = [u for u in users if u["channel_key"] == channel_filter]

    # 📅 Сортировка
    if sort_latest:
        users.sort(key=lambda x: x["payment_date"] or "", reverse=True)
    else:
        users.sort(key=lambda x: x["name"])

    if not users:
        await message.reply_text("⚠️ Подходящих пользователей не найдено.")
        return

    context.user_data["history_state"] = {
        "users": users,
        "page": 0,
        "query": query,
    }

    from utils.pagination import send_history_page
    await send_history_page(message, context)

    # 🔰 Заголовок
    if channel_filter:
        channel_info = fetch_channels().get(channel_filter)
        title = channel_info["title"] if channel_info else channel_filter.capitalize()
        await message.reply_text(f"📋 Пользователи канала <b>{title}</b> ({len(users)} чел.)", parse_mode="HTML")
    elif query:
        await message.reply_text(f"📋 Найдено пользователей: <b>{len(users)}</b>", parse_mode="HTML")


from keyboards.main import build_admin_panel, build_admin_reply_keyboard

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только для администратора.")
        return

    # Покажем reply-клавиатуру с кнопкой /admin
    await update.message.reply_text(
        "🛠 Панель администратора",
        reply_markup=build_admin_reply_keyboard()
    )

    # Отдельным сообщением — inline-кнопки
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=build_admin_panel()
    )
WAITING_FOR_NAME, WAITING_FOR_DATE = range(2)

async def update_pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from db import is_admin  # или импорт заранее, если ещё не сделан

    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ Только для администратора.")

    await update.message.reply_text(
        "📝 Введите имя или username пользователя, которому нужно изменить дату последней оплаты:"
    )
    return WAITING_FOR_NAME


def get_admin_handlers():
    return [
        CommandHandler("list_unpaid", list_unpaid),
        CommandHandler("invite", invite),
        CommandHandler("broadcast", broadcast),
        CommandHandler("list_paid", list_paid),
        CommandHandler("history", history),
        CommandHandler("admin", admin_panel),
    ]