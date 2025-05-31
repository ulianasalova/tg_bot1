from keyboards.main import build_user_cancel_button
from utils.formatting import format_user_card_simple
from keyboards.main import build_user_confirm_button

PAGE_SIZE = 10

async def send_paid_users_page(message, context):
    state = context.user_data.get("paid_list")
    if not state:
        await message.reply_text("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await message.reply_text("⚠️ На этой странице нет пользователей.")
        return

    for user_id, name, status, username, channel_key, payment_date in page_users:
        card = format_user_card_simple(user_id, name, username, channel_key, payment_date)
        await message.reply_text(
            card,
            parse_mode="HTML",
            reply_markup=build_history_keyboard(user_id, status, channel_key, payment_date)
        )

    # Кнопки навигации
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="paid_page:prev"))
    if end < len(users):
        buttons.append(InlineKeyboardButton("➡️ Вперёд", callback_data="paid_page:next"))

    if buttons:
        await message.reply_text("📄 Навигация:", reply_markup=InlineKeyboardMarkup([buttons]))

def build_pagination_keyboard(page: int, total: int, prefix: str = "history_page", page_size: int = 10):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅ Назад", callback_data=f"{prefix}:prev"))
    if (page + 1) * page_size < total:
        buttons.append(InlineKeyboardButton("➡ Вперёд", callback_data=f"{prefix}:next"))
    return InlineKeyboardMarkup([buttons]) if buttons else None

async def handle_pagination_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data  # например: paid_page:next

    page_type, direction = data.split(":")
    state_key = {
        "paid_page": "paid_list",
        "unpaid_page": "unpaid_list",
        "history_page": "history_state"
    }.get(page_type)

    if not state_key:
        await query.message.reply_text("❌ Неизвестный тип страницы.")
        return

    state = context.user_data.get(state_key)
    if not state:
        await query.message.reply_text("❌ Нет данных для отображения.")
        return

    if direction == "next":
        state["page"] += 1
    elif direction == "prev" and state["page"] > 0:
        state["page"] -= 1

    if page_type == "paid_page":
        await send_paid_users_page(query.message, context)
    elif page_type == "unpaid_page":
        await send_unpaid_users_page(query.message, context)
    elif page_type == "history_page":
        from handlers.admin import send_history_page
        await send_history_page(query.message, context)

async def send_unpaid_users_page(message, context):
    state = context.user_data.get("unpaid_list")
    if not state:
        await message.reply_text("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await message.reply_text("⚠️ На этой странице нет пользователей.")
        return

    for user_id, name, username, channel_key, payment_date in page_users:
        text = format_user_card_simple(user_id, name, username, channel_key, payment_date)
        await message.reply_text(
            text=text,
            parse_mode="HTML",
            reply_markup=build_user_confirm_button(user_id, channel_key)
        )

    # Кнопки навигации добавлено письмо
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="unpaid_page:prev"))
    if end < len(users):
        buttons.append(InlineKeyboardButton("➡️ Вперёд", callback_data="unpaid_page:next"))

    if buttons:
        await message.reply_text("📄 Навигация:", reply_markup=InlineKeyboardMarkup([buttons]))

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.formatting import format_user_channel_card
from keyboards.main import build_history_keyboard

PAGE_SIZE = 10

async def send_history_page(message, context):
    state = context.user_data.get("history_state")
    if not state:
        await message.reply_text("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await message.reply_text("⚠️ На этой странице нет пользователей.")
        return

    for user in page_users:
        user_id = user["user_id"]
        name = user["name"]
        username = user.get("username")
        channel_key = user["channel_key"]
        payment_status = user["payment_status"]
        payment_date = user["payment_date"]
        previous_date = user.get("previous_date")

        card = format_user_channel_card(
            user_id=user_id,
            name=name,
            username=username,
            channel_key=channel_key,
            payment_status=payment_status,
            payment_date=payment_date,
            previous_date=previous_date
        )

        await message.reply_text(
            text=card,
            parse_mode="HTML",
            reply_markup=build_history_keyboard(user_id, payment_status, channel_key)
        )

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="history_page:prev"))
    if end < len(users):
        nav_buttons.append(InlineKeyboardButton("➡️ Вперёд", callback_data="history_page:next"))

    if nav_buttons:
        await message.reply_text("📄 Навигация:", reply_markup=InlineKeyboardMarkup([nav_buttons]))