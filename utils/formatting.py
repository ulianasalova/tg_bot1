from utils.storage import fetch_channels


def format_user_card(user_id, name, username, channel_key, payment_date=None, previous_date=None, status=None):
    status_text = "✅ Оплачено" if status == "paid" else "❌ Не оплачено"
    date_text = f"📅 Дата оплаты: {payment_date}" if payment_date else "📅 Дата оплаты: —"
    prev_text = f"↩ Предыдущая: {previous_date}" if previous_date else ""

    channel_info = fetch_channels().get(channel_key)
    channel_text = f"📌 Канал: {channel_info['title']}" if channel_info else "📌 Канал: —"

    username_text = f" (@{username})" if username else ""

    return (
        f"👤 {name}{username_text} (ID: <code>{user_id}</code>)\n"
        f"{channel_text}\n"
        f"{date_text}\n"
        f"{prev_text}\n"
        f"💳 Статус: {status_text}"
    )


def format_user_subscription_card(name, user_id, channel_key, payment_date, days_left):
    channel_info = fetch_channels().get(channel_key)
    channel_title = channel_info['title'] if channel_info else "—"

    if payment_date:
        if days_left < 0:
            pay_status = f"⛔ Срок оплаты истёк {abs(days_left)} дн. назад"
        elif days_left == 0:
            pay_status = "⚠️ Оплата сегодня!"
        else:
            pay_status = f"⏳ Осталось {days_left} дн."
    else:
        pay_status = "❌ Дата оплаты не указана"

    return (
        f"📄 <b>Ваша подписка</b>:\n\n"
        f"👤 <b>{name}</b> (ID: <code>{user_id}</code>)\n"
        f"📌 Канал: {channel_title}\n"
        f"📅 Последняя оплата: {payment_date or '—'}\n"
        f"{pay_status}"
    )

def format_user_card_simple(user_id, name, username, channel_key, payment_date):
    username_text = f" (@{username})" if username else ""
    channel_info = fetch_channels().get(channel_key)
    channel_title = channel_info["title"] if channel_info else channel_key
    return (
        f"👤 {name}{username_text} (ID: <code>{user_id}</code>)\n"
        f"📌 Канал: {channel_title}\n"
        f"📅 Оплата: {payment_date}"
    )


def format_user_channel_card(user_id, name, username, channel_key, payment_status, payment_date, previous_date):
    status_text = "✅ Оплачено" if payment_status == "paid" else "❌ Не оплачено"
    date_text = f"📅 Дата оплаты: {payment_date}" if payment_date else "📅 Дата оплаты: —"
    prev_text = f"↩ Предыдущая: {previous_date}" if previous_date else ""

    channel_info = fetch_channels().get(channel_key)
    channel_title = channel_info['title'] if channel_info else f"[{channel_key}]"

    username_text = f" (@{username})" if username else ""

    return (
        f"👤 {name}{username_text} (ID: <code>{user_id}</code>)\n"
        f"📌 Канал: {channel_title}\n"
        f"{date_text}\n"
        f"{prev_text}\n"
        f"💳 Статус: {status_text}"
    )

