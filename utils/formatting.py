from config import Config

def format_user_card(user_id, name, status, payment_date, previous_date, channel_key=None, username=None):
    status_text = "✅ Оплачено" if status == "paid" else "❌ Не оплачено"
    date_text = f"📅 Дата оплаты: {payment_date}" if payment_date else "📅 Дата оплаты: —"
    prev_text = f"↩ Предыдущая: {previous_date}" if previous_date else ""

    if channel_key:
        channel_info = Config.CHANNELS.get(channel_key)
        channel_text = f"📌 Канал: {channel_info['title']}" if channel_info else "📌 Канал: —"
    else:
        channel_text = "📌 Канал: —"

    username_text = f" (@{username})" if username else ""

    return (
        f"👤 {name}{username_text} (ID: <code>{user_id}</code>)\n"
        f"{channel_text}\n"
        f"{date_text}\n"
        f"{prev_text}\n"
        f"💳 Статус: {status_text}"
    )
