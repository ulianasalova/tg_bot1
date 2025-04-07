from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from config import Config
from db import mark_as_paid, postpone_reminder
from keyboards.main import build_paid_button, build_user_confirm_button
from db import mark_as_paid_custom, mark_as_unpaid
from datetime import datetime

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    if query.data == "pay":
        await query.edit_message_text(
            text=(
                "💳 Реквизиты для оплаты:\n\n"
                "Карта: 1234 5678 9012 3456\n"
                "Срок: 12/25\n"
                "Имя: Бабихин Артём Андреевич\n\n"
                "После оплаты нажмите кнопку ниже:"
            ),
            reply_markup=build_paid_button()
        )

    elif query.data == "paid":
        mark_as_paid(user_id)
        await query.edit_message_text("✅ Спасибо! Мы уведомим администратора.")
        await context.bot.send_message(
            chat_id=Config.ADMIN_CHAT_ID,
            text=f"👤 Пользователь {user_name} (ID: {user_id}) сообщил об оплате.",
            reply_markup=build_user_confirm_button(user_id)
        )

    elif query.data == "remind_later":
        postpone_reminder(user_id)
        await query.edit_message_text("⏰ Напоминание будет отправлено завтра.")

    elif query.data.startswith("admin_confirm:"):
        if query.from_user.id != Config.ADMIN_CHAT_ID:
            await query.answer("⛔ Только админ может это подтвердить.", show_alert=True)
            return
        confirmed_user_id = int(query.data.split(":")[1])
        mark_as_paid_custom(
            confirmed_user_id,
            datetime.now().date().isoformat(),
            admin_id=query.from_user.id
        )

        # Получим имя + username через API
        try:
            user = await context.bot.get_chat(confirmed_user_id)
            name = user.first_name or "Без имени"
            username = f"@{user.username}" if user.username else "(без username)"
            full = f"{username} ({name})"
        except:
            full = f"ID {confirmed_user_id}"
        await query.edit_message_text(f"✅ Оплата пользователя {full} подтверждена.")

    elif query.data.startswith("admin_cancel:"):
        if query.from_user.id != Config.ADMIN_CHAT_ID:
            await query.answer("⛔ Только админ может это отменить.", show_alert=True)
            return

        user_id = int(query.data.split(":")[1])
        mark_as_unpaid(user_id, admin_id=query.from_user.id)

        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name or "Без имени"
            username = f"@{user.username}" if user.username else "(без username)"
            full = f"{username} ({name})"
        except:
            full = f"ID {user_id}"

        await query.edit_message_text(f"↩ Оплата пользователя {full} отменена.")

        await context.bot.send_message(
            chat_id=Config.ADMIN_CHAT_ID,
            text=f"⚠️ Оплата отменена вручную: {full}\n🔄 Администратор вернул статус 'не оплачено'"
        )
    elif query.data.startswith("admin_view:"):
        view = query.data.split(":")[1]

        # Преобразуем кнопку в вызов history с аргументами
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

    elif query.data == "admin_stats":
        from db import get_all_users
        users = get_all_users()

        total = len(users)
        paid = len([u for u in users if u[2] == "paid"])
        not_paid = total - paid

        percent = round((paid / total) * 100, 1) if total > 0 else 0

        latest_user = None
        latest_date = ""
        for u in sorted(users, key=lambda x: x[3] or "", reverse=True):
            if u[2] == "paid" and u[3]:
                latest_user = u
                latest_date = u[3]
                break

        if latest_user:
            try:
                user_chat = await context.bot.get_chat(latest_user[0])
                name = user_chat.first_name or latest_user[1]
                username = f"@{user_chat.username}" if user_chat.username else ""
                latest_info = f"{latest_date} ({name} {username})"
            except:
                latest_info = f"{latest_date} (ID {latest_user[0]})"
        else:
            latest_info = "—"

        await query.message.reply_text(
            text=(
                f"📊 <b>Текущая статистика</b>:\n\n"
                f"👥 Всего пользователей: <b>{total}</b>\n"
                f"✅ Оплатили: <b>{paid}</b>\n"
                f"❌ Не оплатили: <b>{not_paid}</b>\n"
                f"💳 Процент оплат: <b>{percent}%</b>\n"
                f"🆕 Последняя оплата: <b>{latest_info}</b>"
            ),
            parse_mode="HTML"
        )


    elif query.data == "admin_export_csv":
        from db import get_all_users
        import csv
        users = get_all_users()
        file_path = "users_export.csv"
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as f:  # <-- вот ключ
            writer = csv.writer(f)
            writer.writerow(["id", "name", "payment_status", "payment_date", "previous_payment_date", "next_reminder_date"])
            for row in users:
                writer.writerow(row)
        with open(file_path, "rb") as f:
            await query.message.reply_document(document=f, filename="users_export.csv",
                                               caption="📥 Экспорт с кириллицей готов!")

    elif query.data.startswith("user_log:"):
        user_id = int(query.data.split(":")[1])

        from db import get_user_payment_log
        logs = get_user_payment_log(user_id)

        if not logs:
            await query.answer("История пуста", show_alert=True)
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

        await query.answer()  # закрыть "загрузка..."
        await query.message.reply_text(text)



    elif query.data == "come_back":

        await query.edit_message_text("❤️ Мы вас очень ждём! Возвращайтесь как можно скорее!")

        # ⬇ Уведомление администратору — вставляем только сюда

        try:

            user = query.from_user

            name = user.first_name or "Без имени"

            username = f"@{user.username}" if user.username else "(без username)"

            full = f"{name} {username}"

            user_id = user.id

            await context.bot.send_message(

                chat_id=Config.ADMIN_CHAT_ID,

                text=(

                    f"🔔 Пользователь <b>{full}</b> нажал кнопку \"Я вернусь\".\n"

                    f"🆔 ID: <code>{user_id}</code>"

                ),

                parse_mode="HTML"

            )

        except Exception as e:

            print(f"Ошибка при уведомлении админа: {e}")


def get_button_handler():
    return CallbackQueryHandler(handle_button)
