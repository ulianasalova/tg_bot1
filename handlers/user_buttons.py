from telegram import Update
from keyboards.main import build_paid_button
from telegram.ext import ContextTypes, CallbackQueryHandler
from logger import logger
from keyboards.main import build_main_menu
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.storage import fetch_channels

def add_main_menu_button(keyboard_rows):
    if isinstance(keyboard_rows, tuple):
        keyboard_rows = list(keyboard_rows)
    keyboard_rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard_rows)


async def handle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Нажата кнопка: {update.callback_query.data}")
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = query.from_user
    data = query.data


    from db import (
        get_user_channels, get_user_by_id, get_admins_for_channel,
         mark_as_paid_custom, postpone_reminder, mark_user_come_back
    )
    from keyboards.main import build_user_confirm_button, build_channel_keyboard
    from utils.notifications import notify_admins

    from datetime import datetime, timedelta
    from telegram import InlineKeyboardButton

    if data == "pay":
        channels = get_user_channels(user_id)

        if not channels:
            await query.edit_message_text("❌ У вас нет активных подписок.")
            return

        if len(channels) == 1:
            # Один канал — сразу реквизиты
            channel_key = channels[0]["channel_key"]
            await show_payment_details(query, context, user, channel_key)
        else:
            # Несколько каналов — кнопки выбора
            keyboard_rows = [
                [InlineKeyboardButton(fetch_channels()[ch["channel_key"]]["title"],
                                      callback_data=f"pay_channel:{ch['channel_key']}")]
                for ch in channels
            ]

            keyboard = add_main_menu_button(keyboard_rows)

            await query.edit_message_text(
                "💳 Выберите канал, по которому хотите произвести оплату:",
                reply_markup=keyboard
            )


    # 🔹 Оплата по выбранному каналу
    elif data.startswith("pay_channel:"):
        channel_key = data.split(":")[1]
        await show_payment_details(query, context, user, channel_key)

    # 🔹 Подтвердить оплату
    elif data.startswith("paid:"):
        channel_key = data.split(":")[1]
        mark_as_paid_custom(user_id=user_id, channel_key=channel_key, payment_date=datetime.now().date().isoformat())

        await query.edit_message_text(
            "✅ Спасибо! Мы уведомим администратора.",
            reply_markup=add_main_menu_button([])
        )

        channel_info = fetch_channels().get(channel_key)
        channel_title = channel_info["title"] if channel_info else "не выбран"

        admin_ids = get_admins_for_channel(channel_key)

        text = (
            f"👤 Пользователь {user.first_name} (ID: {user_id}) сообщил об оплате.\n"
            f"📌 Канал: {channel_title}"
        )
        await notify_admins(context.bot, text, admin_ids, parse_mode=None)

        if admin_ids:
            await context.bot.send_message(
                chat_id=admin_ids[0],
                text="⬆ Подтвердите оплату:",
                reply_markup=build_user_confirm_button(user_id, channel_key)
            )

    elif data == "main_menu":
        await query.edit_message_text("🏠 Главное меню:", reply_markup=build_main_menu())


    # 🔹 Моя подписка
    elif data == "my_subscription":
        user_data = get_user_by_id(user_id)
        if not user_data:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе.")
            return

        name = user_data["name"]
        username = user_data["username"]
        channels = user_data["subscriptions"]

        if not channels:
            await query.edit_message_text(
                "📭 У вас нет активных подписок.",
                reply_markup=add_main_menu_button([])
            )
            return

        message_lines = [f"📄 <b>Подписки пользователя {name}</b> (ID: <code>{user_id}</code>):\n"]
        for ch in channels:
            channel_key = ch["channel_key"]
            payment_date = ch["payment_date"]
            previous_date = ch["previous_payment_date"]

            channel_info = fetch_channels().get(channel_key)
            channel_title = channel_info["title"] if channel_info else channel_key

            if payment_date:
                try:
                    pay_date = datetime.strptime(payment_date, "%Y-%m-%d")
                    next_due = pay_date + timedelta(days=30)
                    today = datetime.now().date()
                    days_left = (next_due.date() - today).days
                    if days_left < 0:
                        pay_status = f"⛔ Срок истёк {abs(days_left)} дн. назад"
                    elif days_left == 0:
                        pay_status = "⚠️ Оплата сегодня!"
                    else:
                        pay_status = f"⏳ Осталось {days_left} дн."
                except:
                    pay_status = "⚠️ Ошибка в дате"
            else:
                pay_status = "❌ Не оплачено"

            line = (
                f"\n<b>{channel_title}</b>\n"
                f"📅 Последняя оплата: {payment_date or '—'}\n"
                f"{pay_status}"
            )
            message_lines.append(line)

        await query.edit_message_text(
            "\n".join(message_lines),
            parse_mode="HTML",
            reply_markup=add_main_menu_button([])  # 👈 добавили кнопку
        )

    # 🔹 Остальные кнопки
    elif data.startswith("remind_later:"):
        channel_key = data.split(":")[1]
        postpone_reminder(user_id, channel_key)
        await query.edit_message_text("⏰ Напоминание будет отправлено завтра.")



    elif data in ("info", "channel_info"):
        text = "\n\n".join([
            f"<b>{c['title']}</b>\n{c['description']}"
            for c in fetch_channels().values()
        ])
        text += "\n\n<i>Оплата за месячную подписку на любой из каналов <b>1500 рублей</b></i>"

        await query.message.edit_text(text, parse_mode="HTML")

        await query.edit_message_text(
            text="ℹ️ <b>Информация о каналах</b>\n\n" + text,
            parse_mode="HTML",
            reply_markup=add_main_menu_button([])
        )


    elif data == "contact_admin":
        await query.edit_message_text("📩 Связь с админом: @Babikhin_Artem")


    elif data.startswith("come_back:"):
        from datetime import datetime, timedelta
        from utils.scheduler import schedule_check_come_back
        from db import mark_user_as_expired
        channel_key = data.split(":")[1]
        mark_user_as_expired(user_id, channel_key)
        await query.edit_message_text("❤️ Мы вас очень ждём! Возвращайтесь как можно скорее!")
        try:
            full = f"{user.first_name} (@{user.username})" if user.username else user.first_name
            await notify_admins(
                bot=context.bot,
                text=f"🔔 Пользователь <b>{full}</b> нажал кнопку \"Я вернусь\".\n🆔 ID: <code>{user.id}</code>",
                channel_key=channel_key,
                parse_mode="HTML"
            )
            mark_user_come_back(user_id, channel_key)
            # Планируем напоминание админу через 7 дней
            schedule_check_come_back(context.bot, user_id, full, delay_days=7)

        except Exception as e:
            print(f"Ошибка при обработке 'Я вернусь' для пользователя {user_id}: {e}")


    elif data == "choose_channel":
        keyboard = build_channel_keyboard()
        reply_markup = add_main_menu_button(list(keyboard.inline_keyboard))  # 👈 фикс
        await query.edit_message_text(
            "Выберите канал для подписки:",
            reply_markup=reply_markup
        )

    elif data.startswith("set_channel:"):
        channel_key = data.split(":")[1]
        if channel_key not in fetch_channels():
            await query.answer("❌ Канал не найден", show_alert=True)
            return

        from db import add_user_channel
        add_user_channel(user.id, channel_key)

        channel = fetch_channels()[channel_key]
        await query.edit_message_text(
            f"✅ Вы выбрали канал:\n<b>{channel['title']}</b>\nПосле оплаты подписки вы получите к нему доступ!",
            parse_mode="HTML",
            # reply_markup=build_paid_button(channel_key)
        )

        await query.message.reply_text(
            text="💳 Отлично! Теперь можно перейти к оплате подписки 👇",
            reply_markup=add_main_menu_button([
                [InlineKeyboardButton("💳 Оплатить", callback_data=f"pay_channel:{channel_key}")]
            ])
        )

# 📌 Вспомогательная функция: показать реквизиты оплаты
async def show_payment_details(query, context, user, channel_key):
    from db import get_admins_for_channel, get_admin_by_id, get_superadmin_ids
    admin_ids = get_admins_for_channel(channel_key)

    payment_text = "💳 Реквизиты не найдены. Обратитесь к администратору."
    found = False

    for admin_id in admin_ids:
        admin = get_admin_by_id(admin_id)
        if admin and not admin["is_superadmin"] and admin.get("payment_details"):
            clean_details = admin["payment_details"].replace("\\n", "\n")
            payment_text = f"💳 Реквизиты для оплаты:\n\n{clean_details}"
            found = True
            break

    await query.edit_message_text(
        text=payment_text,
        reply_markup=build_paid_button(channel_key)
    )

    if not found:
        superadmins = get_superadmin_ids()
        for superadmin_id in superadmins:
            try:
                await context.bot.send_message(
                    chat_id=superadmin_id,
                    text=(
                        f"⚠️ У пользователя {user.first_name} (ID: {user.id}) нет реквизитов для оплаты.\n"
                        f"Канал: {channel_key}"
                    )
                )
            except Exception as e:
                print(f"Ошибка при уведомлении суперадмина {superadmin_id}: {e}")

def get_user_button_handler():
    return CallbackQueryHandler(
        handle_user_buttons,
        pattern=(
            r"^("
            r"choose_channel|"
            r"set_channel:.*|"
            r"channel_info|"
            r"info|"
            r"pay|"
            r"pay_channel:.*|"
            r"paid:.*|"
            r"remind_later(:.*)?|"  # 🛠 ВАЖНО: добавили '|'
            r"status|"
            r"contact_admin|"
            r"my_subscription|"
            r"come_back(:.*)?|"
            r"main_menu"
            r")$"
        )
    )
