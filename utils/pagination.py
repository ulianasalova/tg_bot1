from keyboards.main import build_user_cancel_button
from utils.formatting import format_user_card_simple
from keyboards.main import build_user_confirm_button

PAGE_SIZE = 10


def build_pagination_keyboard(page: int, total: int, prefix: str, page_size: int = 10):
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

    # Удаляем старую панель навигации (где была кнопка "вперёд/назад")
    await query.message.delete()

    # Вызываем функцию отображения страницы
    if page_type == "paid_page":
        await send_paid_users_page(update.effective_chat, context)
    elif page_type == "unpaid_page":
        await send_unpaid_users_page(update.effective_chat, context)
    elif page_type == "history_page":
        await send_history_page(update.effective_chat, context)


async def send_paid_users_page(chat, context):
    state = context.user_data.get("paid_list")
    if not state:
        await chat.send_message("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await chat.send_message("⚠️ На этой странице нет пользователей.")
        return

    for user_id, name, payment_status, username, channel_key, payment_date in page_users:
        card = format_user_card_simple(user_id, name, username, channel_key, payment_date)
        await chat.send_message(
            card,
            parse_mode="HTML",
            reply_markup=build_user_cancel_button(user_id, channel_key)
        )

        # Кнопки навигации
        # И добавь кнопку навигации в конце
    nav_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Назад", callback_data="paid_page:prev"),
        InlineKeyboardButton("➡️ Вперёд", callback_data="paid_page:next"),
    ]])
    await chat.send_message("📄 Навигация:", reply_markup=nav_markup)


async def send_unpaid_users_page(chat, context):
    state = context.user_data.get("unpaid_list")
    if not state:
        await chat.send_message("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await chat.send_message("⚠️ На этой странице нет пользователей.")
        return

    for user_id, name, status, username, channel_key, payment_date in page_users:
        main_text = format_user_card_simple(user_id, name, username, channel_key, payment_date)
        full_text = f"{main_text}\n\nℹ️ Или напишите /update_pay чтобы изменить дату"

        await chat.send_message(
            text=full_text,
            parse_mode="HTML",
            reply_markup=build_user_confirm_button(user_id, channel_key)
        )


    # И добавь кнопку навигации в конце
    nav_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Назад", callback_data="unpaid_page:prev"),
        InlineKeyboardButton("➡️ Вперёд", callback_data="unpaid_page:next"),
    ]])
    await chat.send_message("📄 Навигация:", reply_markup=nav_markup)

       # Кнопки навигации добавлено письмо


from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.formatting import format_user_channel_card
from keyboards.main import build_history_keyboard

async def send_history_page(chat, context):
    state = context.user_data.get("history_state")
    if not state:
        await chat.send_message("❌ Нет данных для отображения.")
        return

    users = state["users"]
    page = state["page"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_users = users[start:end]

    if not page_users:
        await chat.send_message("⚠️ На этой странице нет пользователей.")
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

        await chat.send_message(
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
        await chat.send_message  ("📄 Навигация:", reply_markup=InlineKeyboardMarkup([nav_buttons]))
