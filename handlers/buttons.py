from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from config import Config
from db import mark_as_paid, postpone_reminder, mark_as_paid_custom, mark_as_unpaid, get_user_channel, get_user_by_id
from keyboards.main import (
    build_paid_button,
    build_user_confirm_button,
    build_channel_filter_keyboard
)
from datetime import datetime
import csv
from utils.formatting import format_user_card

# ✅ Обработчик кнопок от пользователей
async def handle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = query.from_user
    data = query.data

    if data == "pay":
        await query.edit_message_text(
            "💳 Реквизиты для оплаты:\n\n🔹 Карта: 1234 5678 9012 3456\n🔹 Назначение: Подписка SwimGlide",
            reply_markup=build_paid_button()
        )
    elif data == "paid":
        mark_as_paid(user_id)
        await query.edit_message_text("✅ Спасибо! Мы уведомим администратора.")

        from db import get_user_channel
        from utils.notifications import notify_admins

        channel_key = get_user_channel(user_id)
        channel_info = Config.CHANNELS.get(channel_key)
        channel_title = channel_info["title"] if channel_info else "не выбран"

        await notify_admins(
            bot=context.bot,
            text=(
                f"👤 Пользователь {user.first_name} (ID: {user_id}) сообщил об оплате.\n"
                f"📌 Канал: {channel_title}"
            )
        )

        await context.bot.send_message(
            chat_id=Config.ADMIN_CHAT_IDS[0],  # только в первый чат — где будут кнопки
            text="⬆ Подтвердите оплату:",
            reply_markup=build_user_confirm_button(user_id)
        )

    elif data == "remind_later":
        postpone_reminder(user_id)
        await query.edit_message_text("⏰ Напоминание будет отправлено завтра.")

    elif data == "info":
        text = "\n\n".join([
            f"<b>{c['title']}</b>\n{c['description']}"
            for c in Config.CHANNELS.values()
        ])
        await query.edit_message_text(text, parse_mode="HTML")
    elif data == "channel_info":
        text = "\n\n".join([
            f"<b>{c['title']}</b>\n{c['description']}"
            for c in Config.CHANNELS.values()
        ])
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "my_subscription":
        from db import get_user_by_id
        from datetime import datetime, timedelta
        user_id = query.from_user.id
        user_data = get_user_by_id(user_id)

        if not user_data:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе.")
            return
        _, name, status, payment_date, _, channel_key, username = user_data
        # Название канала
        channel_info = Config.CHANNELS.get(channel_key)
        channel_title = channel_info['title'] if channel_info else "—"
        # Срок оплаты

        if payment_date:
            try:
                pay_date = datetime.strptime(payment_date, "%Y-%m-%d")
                next_due_date = pay_date + timedelta(days=30)
                today = datetime.now().date()
                days_left = (next_due_date.date() - today).days
                if days_left < 0:
                    pay_status = f"⛔ Срок оплаты истёк {abs(days_left)} дн. назад"
                elif days_left == 0:
                    pay_status = "⚠️ Оплата сегодня!"
                else:
                    pay_status = f"⏳ Осталось {days_left} дн."
            except:
                pay_status = "⚠️ Некорректная дата оплаты"
        else:

            pay_status = "❌ Дата оплаты не указана"

        text = (
            f"📄 <b>Ваша подписка</b>:\n\n"
            f"👤 <b>{name}</b> (ID: <code>{user_id}</code>)\n"
            f"📌 Канал: {channel_title}\n"
            f"📅 Последняя оплата: {payment_date or '—'}\n"
            f"{pay_status}"
        )
        await query.edit_message_text(text, parse_mode="HTML")


    elif data == "contact_admin":
        await query.edit_message_text("📩 Связь с админом: @ulianasalova")

    elif data == "come_back":
        await query.edit_message_text("❤️ Мы вас очень ждём! Возвращайтесь как можно скорее!")

        try:
            name = user.first_name or "Без имени"
            username = f"@{user.username}" if user.username else "(без username)"
            full = f"{name} {username}"

            from utils.notifications import notify_admins
            await notify_admins(
                bot=context.bot,
                text=(
                    f"🔔 Пользователь <b>{full}</b> нажал кнопку \"Я вернусь\".\n"
                    f"🆔 ID: <code>{user.id}</code>"
                ),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Ошибка при уведомлении админа: {e}")


    elif data == "choose_channel":
        await query.edit_message_text("Выберите канал для подписки:", reply_markup=build_channel_keyboard())


    elif data.startswith("set_channel:"):
        channel_key = data.split(":")[1]
        channel = Config.CHANNELS.get(channel_key)
        if not channel:
            await query.answer("❌ Ошибка выбора канала", show_alert=True)
            return
        from db import update_user_channel
        update_user_channel(query.from_user.id, channel_key)
        await query.edit_message_text(f"✅ Вы выбрали: {channel['title']}")

        # ⬇ Отправляем сразу кнопку "Оплатить"

        await query.message.reply_text(
            text="💳 Отлично! Теперь можно перейти к оплате подписки 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатить", callback_data="pay")]
            ])

        )
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from keyboards.main import build_channel_keyboard

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "ℹ️ Информация о каналах":
        text = "\n\n".join([
            f"<b>{c['title']}</b>\n{c['description']}"
            for c in Config.CHANNELS.values()
        ])
        await update.message.reply_text(text, parse_mode="HTML")

    elif text == "📄 Моя подписка":
        from db import get_user_by_id
        user_data = get_user_by_id(user_id)
        if user_data:
            from utils.formatting import format_user_card
            await update.message.reply_text(
                format_user_card(*user_data),
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("🚫 Вы пока не зарегистрированы.")

    elif text == "💳 Оплата":
        await update.message.reply_text(
            "💳 Реквизиты для оплаты:\n\n🔹 Карта: 1234 5678 9012 3456\n🔹 +79181234393\n🔹 Бабихин Артём Андреевич"
        )

    elif text == "🧾 Выбрать канал":
        await update.message.reply_text(
            "Выберите канал для подписки:",
            reply_markup=build_channel_keyboard()
        )

    elif text == "📩 Написать админу":
        await update.message.reply_text("📩 Связь с админом: @ulianasalova")

# ✅ Обработчик кнопок от администратора

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("admin_confirm:"):
        from db import get_user_by_id
        if query.from_user.id not in Config.ADMIN_CHAT_IDS:
            await query.answer("⛔ Только админ может это подтвердить.", show_alert=True)
            return
        confirmed_user_id = int(data.split(":")[1])
        mark_as_paid_custom(confirmed_user_id, datetime.now().date().isoformat(), admin_id=query.from_user.id)
        try:
            user = await context.bot.get_chat(confirmed_user_id)
            username = f"@{user.username}" if user.username else "(без username)"
            full = f"{username} ({user.first_name})"
        except:
            full = f"ID {confirmed_user_id}"

        user_data = get_user_by_id(confirmed_user_id)
        text = format_user_card(*user_data)
        await query.edit_message_text(f"✅ Подтверждена оплата:\n\n{text}")

    elif data.startswith("admin_cancel:"):
        if query.from_user.id not in Config.ADMIN_CHAT_IDS:
            await query.answer("⛔ Только админ может это отменить.", show_alert=True)
            return

        user_id = int(data.split(":")[1])
        mark_as_unpaid(user_id, admin_id=query.from_user.id)

        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "(без username)"
            full = f"{username} ({user.first_name})"
        except:
            full = f"ID {user_id}"

        from db import get_user_by_id
        user_data = get_user_by_id(user_id)
        text = format_user_card(*user_data)

        await query.edit_message_text(f"↩ Отмена оплаты:\n\n{text}")

        from utils.notifications import notify_admins
        await notify_admins(
            bot=context.bot,
            text=(
                f"⚠️ Оплата отменена вручную: {full}\n"
                f"🔄 Администратор вернул статус 'не оплачено'"
            )
        )


    elif data.startswith("admin_view:"):
        view = data.split(":")[1]
        args = []
        if view == "paid":
            args = ["only=paid"]
        elif view == "not_paid":
            args = ["only=not_paid"]
        elif view == "latest":
            args = ["only=paid", "sort=latest"]

        update = Update.de_json(update.to_dict(), context.bot)
        context.args = args

        from handlers.admin import history
        await history(update, context)


    elif data == "admin_stats":
        from db import get_all_users
        from collections import defaultdict
        users = get_all_users()
        total = len(users)
        paid = len([u for u in users if u[2] == "paid"])
        not_paid = total - paid
        percent = round((paid / total) * 100, 1) if total > 0 else 0

        # 🔹 Последняя оплата

        latest_user = None
        for u in sorted(users, key=lambda x: x[3] or "", reverse=True):
            if u[2] == "paid" and u[3]:
                latest_user = u
                break
        if latest_user:
            try:
                user_chat = await context.bot.get_chat(latest_user[0])
                username = f"@{user_chat.username}" if user_chat.username else ""
                latest_info = f"{latest_user[3]} ({user_chat.first_name} {username})"

            except:
                latest_info = f"{latest_user[3]} (ID {latest_user[0]})"
        else:
            latest_info = "—"
        # 🔹 Подсчёт по каналам

        channels_stats = defaultdict(lambda: {"total": 0, "paid": 0})
        for u in users:
            channel = u[5] or "—"  # channel_key (может быть None)
            channels_stats[channel]["total"] += 1
            if u[2] == "paid":
                channels_stats[channel]["paid"] += 1

        # 🔹 Формируем блок статистики по каналам

        channel_lines = ""
        for key, stats in channels_stats.items():
            info = Config.CHANNELS.get(key)
            title = info["title"] if info else "Без канала"
            channel_lines += (
                f"\n🏷 <b>{title}</b>:\n"
                f"— всего: <b>{stats['total']}</b>\n"
                f"— оплатили: <b>{stats['paid']}</b>\n"
            )

        # 🔹 Ответ

        await query.message.reply_text(

            text=(
                f"📊 <b>Текущая статистика</b>:\n\n"
                f"👥 Всего пользователей: <b>{total}</b>\n"
                f"✅ Оплатили: <b>{paid}</b>\n"
                f"❌ Не оплатили: <b>{not_paid}</b>\n"
                f"💳 Процент оплат: <b>{percent}%</b>\n"
                f"{channel_lines}\n"
                f"🆕 Последняя оплата: <b>{latest_info}</b>"
            ),
            parse_mode="HTML"
        )
    elif data.startswith("admin_filter:"):
        # Получаем канал из callback_data
        channel_key = data.split(":")[1]

        from handlers.admin import history
        update = Update.de_json(update.to_dict(), context.bot)

        if channel_key == "all":
            context.args = []  # Без фильтров — все
        else:
            context.args = [f"channel={channel_key}"]

        await history(update, context)
    elif data == "admin_all_users":
        await query.message.edit_text("🔍 Выберите фильтр:", reply_markup=build_channel_filter_keyboard())

    elif data.startswith("history_page:"):
        state = context.user_data.get("history_state")
        if not state:
            await query.answer("❌ Нет данных", show_alert=True)
            return

        if data == "history_page:next":
            state["page"] += 1
        elif data == "history_page:prev" and state["page"] > 0:
            state["page"] -= 1

        await send_history_page(query.message, context)



    elif data.startswith("admin_export_csv"):

        from db import get_all_users_csv
        users = get_all_users_csv()
        # Разбираем параметры из callback_data, например: admin_export_csv:paid:swimmasters
        parts = data.split(":")
        status_filter = parts[1] if len(parts) > 1 and parts[1] else None
        channel_filter = parts[2] if len(parts) > 2 and parts[2] else None

        # Применяем фильтрацию

        if status_filter:
            users = [u for u in users if u[2] == status_filter]
        if channel_filter:
            users = [u for u in users if u[5] == channel_filter]

        # Создаём CSV

        file_path = "users_export.csv"
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["id", "name", "payment_status", "payment_date", "previous_payment_date", "channel", "username"])
            for row in users:
                writer.writerow(row)
        with open(file_path, "rb") as f:
            await query.message.reply_document(
                f,
                filename="users_export.csv",
                caption="📥 Файл успешно создан и загружен!"
            )


    elif data.startswith("user_log:"):
        user_id = int(data.split(":")[1])
        from db import get_user_payment_log
        logs = get_user_payment_log(user_id)
        if not logs:
            await query.answer("История пуста", show_alert=True)
            return
        text = f"📜 История пользователя {user_id}:\n\n"
        for log in logs:
            date_logged, action, old_date, new_date, by_admin = log
            if action == "confirmed":
                text += f"✅ {date_logged[:10]} — подтверждена оплата (новая: {new_date})\n"
            elif action == "cancelled":
                text += f"🔴 {date_logged[:10]} — отмена оплаты (старая: {old_date})\n"
            else:
                text += f"⚙️ {date_logged[:10]} — действие: {action}\n"
        await query.answer()
        await query.message.reply_text(text)


# 👉 Регистрируем хендлеры в bot.py
def get_user_button_handler():
    return CallbackQueryHandler(handle_user_buttons, pattern=r"^(choose_channel|set_channel:.*|channel_info|info|pay|paid|remind_later|status|contact_admin|my_subscription|come_back)$")


def get_admin_button_handler():
    return CallbackQueryHandler(handle_admin_buttons, pattern=r"^(admin_.*|user_log:.*|filter_channel:.*)$")

