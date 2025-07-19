from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

from datetime import datetime, timedelta
from db import get_all_users, mark_user_as_expired
from keyboards.main import build_reminder_keyboard, build_comeback_keyboard

# Устанавливаем московский часовой пояс
moscow = pytz.timezone("Europe/Moscow")

scheduler = AsyncIOScheduler()


async def send_reminders(bot):
    print(f"🕒 [{datetime.now()}] Запуск планового напоминания")
    today = datetime.now().date()
    users = get_all_users()
    import html
    for user in users:
        user_id, name, status, payment_date_str, next_reminder_str, channel_key, channel_title = user
        safe_title = html.escape(channel_title)
        # 🛡️ Пропускаем пользователей со статусом "come_back"
        if status == "come_back":
            continue
        try:
            if status == "paid" and payment_date_str:
                payment_date = datetime.fromisoformat(payment_date_str).date()
                remind_date = payment_date + timedelta(days=28)
                expire_date = payment_date + timedelta(days=31)

                if remind_date <= today < expire_date:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🏊‍♀️ Привет, {html.escape(name)}!\n"
                            f"Скоро заканчивается твоя подписка.\n"
                            f"на канал <b>{safe_title}</b>\n"
                            "Пожалуйста, продли её 💳"
                        ),
                        reply_markup=build_reminder_keyboard(channel_key),
                        parse_mode="HTML"
                    )


                elif today >= expire_date:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "❌ Мы не получили оплату. "
                            f"Доступ к каналу {safe_title}\n"
                            "будет приостановлен 😢\n"
                            "❤️ Мы ждём тебя обратно!"
                        ),

                        reply_markup=build_comeback_keyboard(channel_key)
                    )


            elif next_reminder_str and status == "not_paid":
                next_reminder = datetime.fromisoformat(next_reminder_str).date()
                if next_reminder <= today:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🏊‍♀️ Привет, {name}!\n"
                            "Напоминаем о необходимости внести платёж 💰"
                            f"по подписке {safe_title}"
                        ),
                        reply_markup=build_reminder_keyboard(channel_key)
                    )


        except Exception as e:
            print(f"⚠️ Не удалось отправить пользователю {user_id}: {e}")


def start_scheduler(bot):
    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=11, minute=30, timezone=moscow),
        args=[bot]
    )
    scheduler.start()
    print("✅ Планировщик запущен: каждый день в 11:30 по Москве")


async def notify_admin_about_come_back(bot, user_id: int, user_name: str):
    from db import get_admins_for_channel
    admin_ids = get_admins_for_channel("your_default_channel")  # или всех админов
    text = (
        f"🔔 Пользователь {user_name} (ID: {user_id}) нажал 'Я вернусь' "
        f"{7} дней назад.\n"
        "Проверьте, вернулся ли он к оплате."
    )
    for admin_id in admin_ids:
        await bot.send_message(admin_id, text)


def schedule_check_come_back(bot, user_id: int, user_name: str, delay_days=7):
    run_date = datetime.now() + timedelta(days=delay_days)

    scheduler.add_job(
        notify_admin_about_come_back,
        trigger=DateTrigger(run_date=run_date),
        args=[bot, user_id, user_name],
        id=f"remind_come_back_{user_id}",  # уникальный id задачи
        replace_existing=True
    )
