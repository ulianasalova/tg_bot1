from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from datetime import datetime, timedelta
from db import get_all_users
from keyboards.main import build_reminder_keyboard, build_comeback_keyboard

# Устанавливаем московский часовой пояс
moscow = pytz.timezone("Europe/Moscow")

scheduler = AsyncIOScheduler()

async def send_reminders(bot):
    print(f"🕒 [{datetime.now()}] Запуск планового напоминания")
    today = datetime.now().date()
    users = get_all_users()

    for user in users:
        user_id, name, status, payment_date_str, next_reminder_str = user

        try:
            if status == "paid" and payment_date_str:
                payment_date = datetime.fromisoformat(payment_date_str).date()
                remind_date = payment_date + timedelta(days=27)
                expire_date = payment_date + timedelta(days=30)

                if remind_date <= today < expire_date:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🏊‍♀️ Привет, {name}!\n"
                            "Скоро заканчивается твоя подписка. Пожалуйста, продли её 💳"
                        ),
                        reply_markup=build_reminder_keyboard()
                    )
                elif today >= expire_date:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "❌ Мы не получили оплату. "
                            "Доступ к каналу SwimGlide приостановлен 😢\n"
                            "❤️ Мы ждём тебя обратно!"
                        ),
                        reply_markup=build_comeback_keyboard()
                    )

            elif next_reminder_str:
                next_reminder = datetime.fromisoformat(next_reminder_str).date()
                if next_reminder <= today:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🏊‍♀️ Привет, {name}!\n"
                            "Напоминаем о необходимости внести платёж 💰"
                        ),
                        reply_markup=build_reminder_keyboard()
                    )
        except Exception as e:
            print(f"⚠️ Не удалось отправить пользователю {user_id}: {e}")

def start_scheduler(bot):
    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=10, minute=0, timezone=moscow),
        args=[bot]
    )
    scheduler.start()
    print("✅ Планировщик запущен: каждый день в 10:00 по Москве")
