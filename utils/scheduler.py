from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from datetime import datetime, timedelta
import html

from db import get_all_users, get_admins_for_channel
from keyboards.main import build_reminder_keyboard, build_comeback_keyboard,build_user_confirm_button

moscow = pytz.timezone("Europe/Moscow")
scheduler = AsyncIOScheduler()


async def send_reminders(bot):
    """Асинхронная отправка напоминаний"""
    print(f"🕒 [{datetime.now()}] Запуск планового напоминания")
    today = datetime.now().date()
    users = get_all_users()

    for user in users:
        user_id, name, status, payment_date_str, next_reminder_str, channel_key, channel_title = user
        safe_title = html.escape(channel_title)

        if status == "come_back":
            continue

        try:
            if status == "paid" and next_reminder_str:  # Исправлено: payment_date_str вместо next_reminder_str
                payment_date = datetime.fromisoformat(next_reminder_str).date()
                remind_date = payment_date - timedelta(days=2)
                expire_date = payment_date + timedelta(days=1)

                if remind_date <= today < expire_date:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🏊‍♀️ Привет, {html.escape(name)}!\nСкоро заканчивается подписка на канал <b>{safe_title}</b>",
                        reply_markup=build_reminder_keyboard(channel_key),
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(0.1)
                elif today >= expire_date + timedelta(days=1):
                    # Сообщение пользователю
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Доступ к каналу {safe_title} будет приостановлен",
                        reply_markup=build_comeback_keyboard(channel_key)
                    )
                    # Уведомление всем администраторам
                    admin_ids = get_admins_for_channel(channel_key)
                    admin_message = (
                        f"⚠️ У пользователя приостановлен доступ к каналу\n"
                        f"ID: {user_id}\n"
                        f"Имя: {html.escape(name)}\n"
                        f"Канал: {safe_title}\n"
                        f"Дата окончания: {expire_date}"
                    )

                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(
                                chat_id=admin_id,  # Предполагаем, что admin[0] - это chat_id
                                text=admin_message,
                                reply_markup=build_user_confirm_button(user_id,channel_key),
                                parse_mode="HTML"
                            )
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"⚠️ Ошибка отправки админу {admin_id}: {e}")

        except Exception as e:
            print(f"⚠️ Ошибка отправки пользователю {user_id}: {e}")


async def notify_admin_about_access_revoked(bot, user_id: int, user_name: str, channel_title: str, expire_date):
    """Асинхронное уведомление админа о приостановке доступа"""
    admin_ids = get_admins_for_channel("default_channel")
    text = (
        f"🚫 Доступ приостановлен\n"
        f"Пользователь: {user_name} (ID: {user_id})\n"
        f"Канал: {channel_title}\n"
        f"Дата окончания: {expire_date}"
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"⚠️ Ошибка отправки админу {admin_id}: {e}")


async def notify_admin_about_come_back(bot, user_id: int, user_name: str):
    """Асинхронное уведомление админа"""
    admin_ids = get_admins_for_channel("default_channel")
    text = f"🔔 Пользователь {user_name} (ID: {user_id}) нажал 'Я вернусь'"
    for admin_id in admin_ids:
        await bot.send_message(admin_id, text)


def start_scheduler(bot):
    """Запуск планировщика"""
    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=11, minute=30, timezone=moscow),
        args=[bot]
    )
    scheduler.start()
    print("✅ Планировщик запущен (AsyncIOScheduler)")


def schedule_check_come_back(bot, user_id: int, user_name: str, delay_days=7):
    """Планирование проверки возврата"""
    run_date = datetime.now() + timedelta(days=delay_days)
    scheduler.add_job(
        notify_admin_about_come_back,
        trigger=DateTrigger(run_date=run_date),
        args=[bot, user_id, user_name],
        id=f"remind_come_back_{user_id}",
        replace_existing=True
    )
