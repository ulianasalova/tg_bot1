from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from keyboards.main import build_channel_filter_keyboard, build_history_keyboard
from db import is_admin, mark_as_paid_custom, mark_as_unpaid
from datetime import datetime, timedelta
import csv
from logger import logger
from utils.storage import fetch_channels

# ✅ Обработчик кнопок от администратора

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("paid_page:"):
        from utils.pagination import send_paid_users_page
        state = context.user_data.get("paid_list")
        if not state:
            await query.answer("⚠️ Нет данных", show_alert=True)
            return

        if data == "paid_page:next":
            state["page"] += 1
        elif data == "paid_page:prev" and state["page"] > 0:
            state["page"] -= 1

        await send_paid_users_page(query.message, context)


    elif data == "admin_view:to_confirm":
        from db import get_users_pending_confirmation
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        users = get_users_pending_confirmation()

        if not users:
            await query.edit_message_text("📭 Нет оплат, ожидающих подтверждения.")
            return
        await query.edit_message_text("🧾 Список оплат, ожидающих подтверждения:")
        for user in users:
            user_id, name, username, channel_key, payment_date = user
            channel_title = fetch_channels().get(channel_key, {}).get("title", channel_key)
            username_str = f"@{username}" if username else "(без username)"
            text = (
                f"👤 <b>{name}</b> {username_str} (ID: <code>{user_id}</code>)\n"
                f"📌 Канал: <b>{channel_title}</b>\n"
                f"📅 Дата оплаты: {payment_date}\n"
                f"💳 Статус: <b>Ожидает подтверждения</b>"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm:{user_id}:{channel_key}"),
                    InlineKeyboardButton("↩ Отменить", callback_data=f"admin_cancel:{user_id}:{channel_key}")
                ],
                [
                    InlineKeyboardButton("📜 История", callback_data=f"user_log:{user_id}")
                ]
            ])
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    elif data.startswith("admin_confirm:"):
        if not is_admin(query.from_user.id):
            await query.answer("⛔ Только админ может это подтвердить.", show_alert=True)
            return

        # Извлекаем user_id и channel_key
        parts = data.split(":")
        if len(parts) < 3:
            await query.answer("⚠️ Неверный формат данных", show_alert=True)
            return

        confirmed_user_id = int(parts[1])
        channel_key = parts[2]

        # ✅ Подтверждаем оплату с action='confirmed'
        mark_as_paid_custom(
            user_id=confirmed_user_id,
            channel_key=channel_key,
            payment_date=datetime.now().date().isoformat(),
            admin_id=query.from_user.id,
            action="confirmed"  # ← вот эта строка ключевая
        )

        # ⬇️ Новое: уведомляем пользователя
        channel_info = fetch_channels().get(channel_key)
        channel_title = channel_info["title"] if channel_info else channel_key

        try:
            await context.bot.send_message(
                chat_id=confirmed_user_id,
                text=(
                    f"✅ Ваша подписка на канал <b>{channel_title}</b> подтверждена администратором.\n"
                    f"Приятного пользования! 🎉"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя {confirmed_user_id}: {e}")
        # Получаем Telegram имя
        try:
            user = await context.bot.get_chat(confirmed_user_id)
            username = f"@{user.username}" if user.username else "(без username)"
            full_name = f"{username} ({user.first_name})"
        except Exception as e:
            logger.warning(f"Ошибка при получении имени пользователя: {e}")
            full_name = f"ID {confirmed_user_id}"

        await query.edit_message_text(
            f"✅ Подтверждена оплата от пользователя {full_name} по каналу: <b>{channel_key}</b>",
            parse_mode="HTML"
        )
        # Изменим клавиатуру у этого сообщения
        await query.edit_message_reply_markup(
            reply_markup=build_history_keyboard(confirmed_user_id, "paid", channel_key)
        )


    elif data.startswith("admin_cancel:"):
        parts = data.split(":")

        if len(parts) < 3:
            await query.answer("⚠️ Неверный формат", show_alert=True)
            return

        user_id = int(parts[1])
        channel_key = parts[2]

        if not is_admin(query.from_user.id):
            await query.answer("⛔ Нет доступа", show_alert=True)
            return

        mark_as_unpaid(
            user_id=user_id,
            channel_key=channel_key,
            admin_id=query.from_user.id
        )

        # Получим имя пользователя
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "(без username)"
            name = user.first_name
        except Exception as e:
            logger.warning(f"Ошибка при получении пользователя {user_id}: {e}")
            username = "(недоступен)"
            name = "Без имени"

        text = (
            f"↩ Оплата отменена:\n"
            f"👤 {name} {username}\n"
            f"📌 Канал: <b>{channel_key}</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML")




    elif data.startswith("admin_view:"):
        view = data.split(":")[1]
        args = []
        if view == "paid":
            args = ["only=paid"]
        elif view == "not_paid":
            args = ["only=not_paid"]
        elif view == "latest":
            args = ["only=new_users"]  # ← вот это ключевая строка
        update = Update.de_json(update.to_dict(), context.bot)
        context.args = args
        from handlers.admin import history
        await history(update, context)



    elif data == "admin_stats":
        from db import get_all_users_with_channels
        from collections import defaultdict
        users = get_all_users_with_channels()
        total = len(users)
        paid = len([u for u in users if u["payment_status"] == "paid"])
        not_paid = total - paid
        percent = round((paid / total) * 100, 1) if total > 0 else 0
        # 🔹 Последняя оплата
        latest_user = None
        for u in sorted(users, key=lambda x: x["payment_date"] or "", reverse=True):
            if u["payment_status"] == "paid" and u["payment_date"]:
                latest_user = u
                break
        if latest_user:
            try:
                user_chat = await context.bot.get_chat(latest_user["user_id"])
                username = f"@{user_chat.username}" if user_chat.username else ""
                latest_info = f"{latest_user['payment_date']} ({user_chat.first_name} {username})"
            except:
                latest_info = f"{latest_user['payment_date']} (ID {latest_user['user_id']})"
        else:
            latest_info = "—"
        # 🔹 Подсчёт по каналам

        channel_stats = defaultdict(lambda: {"total": 0, "paid": 0})

        for u in users:
            key = u["channel_key"]
            channel_stats[key]["total"] += 1
            if u["payment_status"] == "paid":
                channel_stats[key]["paid"] += 1
        # 🔹 Формируем блок статистики по каналам
        channel_lines = ""
        for key, stats in channel_stats.items():
            info = fetch_channels().get(key)
            title = info["title"] if info else key
            channel_lines += (
                f"\n🏷 <b>{title}</b>:\n"
                f"— всего: <b>{stats['total']}</b>\n"
                f"— оплатили: <b>{stats['paid']}</b>\n"
            )
        await query.message.reply_text(
            text=(
                f"📊 <b>Текущая статистика</b>:\n\n"
                f"👥 Всего подписок: <b>{total}</b>\n"
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
        admin_id = query.from_user.id
        await query.message.edit_text(
            "🔍 Выберите фильтр:",
            reply_markup=build_channel_filter_keyboard(admin_id)
        )

    elif data.startswith("history_page:"):
        from utils.pagination import send_history_page
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
        from db import get_all_users_with_channels
        users = get_all_users_with_channels()
        admin_id = query.from_user.id
        # Парсим фильтры

        parts = data.split(":")
        status_filter = parts[1] if len(parts) > 1 and parts[1] else None
        channel_filter = parts[2] if len(parts) > 2 and parts[2] else None
        if status_filter:
            users = [u for u in users if u["payment_status"] == status_filter]
        if channel_filter:
            users = [u for u in users if u["channel_key"] == channel_filter]
        file_path = "users_export.csv"
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "name", "payment_status", "payment_date",
                "previous_payment_date", "channel", "username"
            ])

            for u in users:
                writer.writerow([
                    u["user_id"],
                    u["name"],
                    u["payment_status"],
                    u["payment_date"],
                    u["previous_payment_date"],
                    u["channel_key"],
                    u["username"]
                ])

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
        text = f"📜 История пользователя <code>{user_id}</code>:\n\n"
        for log in logs:
            channel_key, date_logged, action, old_date, new_date, by_admin = log
            channel_title = fetch_channels().get(channel_key, {}).get("title", channel_key)
            date_str = date_logged[:10]
            if action == "confirmed":
                text += (
                    f"✅ {date_str} — подтверждена оплата канала <b>{channel_title}</b>\n"
                    f"🔄 Новая дата: {new_date}\n"
                )

            elif action == "cancelled":

                text += (
                    f"🔴 {date_str} — отмена оплаты канала <b>{channel_title}</b>\n"
                    f"⌛ Старая дата: {old_date}\n"
                )

            else:
                text += (
                    f"⚙️ {date_str} — действие: {action} по каналу <b>{channel_title}</b>\n"
                )

        await query.answer()
        await query.message.reply_text(text, parse_mode="HTML")


    elif data.startswith("unpaid_page:"):
        from utils.pagination import send_unpaid_users_page
        state = context.user_data.get("unpaid_list")
        if not state:
            await query.answer("❌ Нет данных", show_alert=True)
            return

        if data == "unpaid_page:next":
            state["page"] += 1
        elif data == "unpaid_page:prev" and state["page"] > 0:
            state["page"] -= 1

        await send_unpaid_users_page(query.message, context)




# 👉 Регистрируем хендлеры в bot.py
def get_admin_button_handler():
    return CallbackQueryHandler(
        handle_admin_buttons,
        pattern=r"^(admin(_|\w)*:?.*|user_log:\d+|filter_channel:.*)$"
    )
