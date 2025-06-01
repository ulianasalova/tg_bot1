from utils.storage import fetch_channels

def build_reminder_keyboard(channel_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Оплатить", callback_data=f"pay_channel:{channel_key}")],
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid:{channel_key}")],
        [InlineKeyboardButton("⏰ Напомнить позже", callback_data=f"remind_later:{channel_key}")],
    ])


def build_paid_button(channel_key=None):
    callback_data = "paid"
    if channel_key:
        callback_data = f"paid:{channel_key}"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=callback_data)],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])


def build_user_confirm_button(user_id: int, channel_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm:{user_id}:{channel_key}")],
        [InlineKeyboardButton("✉️ Написать", callback_data=f"message_user:{user_id}")]
    ])

def build_comeback_keyboard(channel_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🙏 Я вернусь позже", callback_data=f"come_back:{channel_key}")],
        [InlineKeyboardButton("💸 Я не могу без вас! Готов оплатить", callback_data=f"pay_channel:{channel_key}")]
    ])


def build_user_cancel_button(user_id: int, channel_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩ Отменить оплату", callback_data=f"admin_cancel:{user_id}:{channel_key}")],
        [InlineKeyboardButton("✉️ Написать", callback_data=f"message_user:{user_id}")]
    ])

def build_admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Все пользователи", callback_data="admin_all_users")],
        [InlineKeyboardButton("‼️ Оплаты на подтверждение", callback_data="admin_view:to_confirm")],  # ← добавили
        [InlineKeyboardButton("✅ Оплатившие", callback_data="admin_view:paid")],
        [InlineKeyboardButton("❌ Не оплатили", callback_data="admin_view:not_paid")],
        [InlineKeyboardButton("🆕 Новые подписчики", callback_data="admin_view:latest")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📥 Экспорт в Excel (CSV)", callback_data="admin_export_csv")]
    ])


from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_admin_channels

def build_channel_filter_keyboard(admin_id: int):
    channels = get_admin_channels(admin_id)  # Получаем список ключей каналов

    keyboard = []

    # 👥 Кнопка для всех каналов админа
    keyboard.append([InlineKeyboardButton("👥 Все", callback_data="admin_filter:all")])

    # 🏷 Кнопки по каждому каналу админа
    for key in channels:
        info = fetch_channels().get(key)
        title = info["title"] if info else key.capitalize()
        keyboard.append([InlineKeyboardButton(title, callback_data=f"admin_filter:{key}")])

    return InlineKeyboardMarkup(keyboard)


def build_history_keyboard(user_id: int, status: str, channel_key: str, payment_date=None):
    from db import is_payment_confirmed

    buttons = []
    payment_confirmed = is_payment_confirmed(user_id, channel_key)

    if status == "paid":
        if not payment_confirmed:
            buttons.append(
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm:{user_id}:{channel_key}")
            )
        buttons.append(
            InlineKeyboardButton("↩ Отменить", callback_data=f"admin_cancel:{user_id}:{channel_key}")
        )
        buttons.append(
            InlineKeyboardButton("✉️ Написать", callback_data=f"message_user:{user_id}")
        )

    elif status == "not_paid":
        # 👇 Добавим кнопку подтверждения для новых пользователей (без даты оплаты)
        if payment_date is None:
            buttons.append(
                InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm:{user_id}:{channel_key}")
            )
            buttons.append(
                InlineKeyboardButton("✉️ Написать", callback_data=f"message_user:{user_id}")
            )

    buttons.append(
        InlineKeyboardButton("📜 История", callback_data=f"user_log:{user_id}")
    )

    return InlineKeyboardMarkup([buttons])



# меню пользователя
def build_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 Выбрать канал", callback_data="choose_channel")],
        [InlineKeyboardButton("💳 Оплатить подписку", callback_data="pay")],
        [InlineKeyboardButton("📄 Моя подписка", callback_data="my_subscription")],
        [InlineKeyboardButton("ℹ️ Информация о каналах", callback_data="channel_info")],
        [InlineKeyboardButton("✉️ Поддержка", url="https://t.me/Babikhin_Artem")],
    ])


def build_channel_keyboard():
    from utils.storage import fetch_channels
    buttons = []

    for key, channel in fetch_channels().items():
        text = channel["title"]
        buttons.append([InlineKeyboardButton(text, callback_data=f"set_channel:{key}")])

    return InlineKeyboardMarkup(buttons)

from telegram import ReplyKeyboardMarkup, KeyboardButton

def build_admin_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("/admin")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
