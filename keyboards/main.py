from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

def build_reminder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Оплатить", callback_data="pay")],
        [InlineKeyboardButton("✅ Я оплатил", callback_data="paid")],
        [InlineKeyboardButton("⏰ Напомнить позже", callback_data="remind_later")],
    ])

def build_paid_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data="paid")]
    ])

def build_user_confirm_button(user_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm:{user_id}")]
    ])

def build_comeback_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🙏 Я вернусь", callback_data="come_back")],
        [InlineKeyboardButton("💸 Я не могу без вас! Готов оплатить", callback_data="pay")]
    ])

def build_user_cancel_button(user_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩ Отменить оплату", callback_data=f"admin_cancel:{user_id}")]
    ])

def build_admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Все пользователи", callback_data="admin_all_users")],
        [InlineKeyboardButton("✅ Оплатившие", callback_data="admin_view:paid")],
        [InlineKeyboardButton("❌ Не оплатили", callback_data="admin_view:not_paid")],
        [InlineKeyboardButton("🆕 Последние оплаты", callback_data="admin_view:latest")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📥 Экспорт в Excel (CSV)", callback_data="admin_export_csv")]

    ])

def build_history_keyboard(user_id: int, status: str):
    buttons = []

    if status == "paid":
        buttons.append(
            InlineKeyboardButton("↩ Отменить оплату", callback_data=f"admin_cancel:{user_id}")
        )
        buttons.append(
            InlineKeyboardButton("✅ Подтвердить заново", callback_data=f"admin_confirm:{user_id}")
        )
    else:
        buttons.append(
            InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm:{user_id}")
        )

    buttons.append(
        InlineKeyboardButton("📜 История", callback_data=f"user_log:{user_id}")
    )

    return InlineKeyboardMarkup([buttons])

def build_channel_filter_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Все", callback_data="admin_filter:all")],
        [InlineKeyboardButton("🏊 Masters", callback_data="admin_filter:swimmasters")],
        [InlineKeyboardButton("👙 Amateur", callback_data="admin_filter:amateur")],
    ])

# меню пользователя
def build_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧾 Выбрать канал", callback_data="choose_channel")],
        [InlineKeyboardButton("ℹ️ Информация о каналах", callback_data="channel_info")],
        [InlineKeyboardButton("💳 Оплатить", callback_data="pay")],
        [InlineKeyboardButton("📄 Моя подписка", callback_data="my_subscription")],
        [InlineKeyboardButton("✉️ Написать админу", url="https://t.me/Babikhin_Artem")] # Заменить имя админа!!!
    ])

def build_channel_keyboard():
    buttons = []

    for key, channel in Config.CHANNELS.items():
        text = channel["title"]
        buttons.append([InlineKeyboardButton(text, callback_data=f"set_channel:{key}")])

    return InlineKeyboardMarkup(buttons)