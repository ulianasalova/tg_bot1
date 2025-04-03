import logging
from sqlite3 import Cursor
import telebot
import sqlite3
import schedule
import time
from telebot import types
import threading


# Укажите ваш токен бота
TOKEN = "8018132574:AAHJaoNpXuomSlf93UwbjB9O5KEIP-xiJ7c"
CHANNEL_ID = "-1002273493973"  # Имя или ID канала
MESSAGE_TEXT = "Напоминаем о необходимости оплаты подписки! Не забудьте продлить доступ."

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)


# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect("subscribers.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY
            )
        """)
        conn.commit()
        conn.close()
        logger.info("База данных и таблица subscribers инициализированы.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")


# Проверка подписки на канал
def is_subscribed(user_id):
    """Проверяет, подписан ли пользователь на канал."""
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        logger.info(f"Статус подписки пользователя {user_id}: {chat_member.status}")
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки пользователя {user_id}: {e}")
        return False


# Добавление подписчика
def add_subscriber(user_id):
    try:
        conn = sqlite3.connect("subscribers.db")
        cursor: Cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Пользователь {user_id} добавлен в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {user_id} в базу данных: {e}")


# Получение списка подписчиков
def get_subscribers():
    try:
        conn = sqlite3.connect("subscribers.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM subscribers")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        logger.info(f"Загружено {len(users)} подписчиков из базы данных.")
        return users
    except Exception as e:
        logger.error(f"Ошибка при получении подписчиков из базы данных: {e}")
        return []


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    logger.info(f"Получена команда /start от пользователя {user_id}")

    if is_subscribed(user_id):
        add_subscriber(user_id)  # Добавляем пользователя в базу
        bot.send_message(user_id, "Вы подписаны на канал и получите напоминания!")
    else:
        bot.send_message(user_id, f"Сначала подпишитесь на канал {CHANNEL_ID} и попробуйте снова.")


def send_subscription_reminder():
    """Отправка личных напоминаний подписчикам."""
    logger.info(f"Запуск напоминания в {time.strftime('%H:%M:%S')}")
    subscribers = get_subscribers()
    logger.info(f"Отправка напоминаний {len(subscribers)} подписчикам.")
    for user_id in subscribers:
        try:

            # Создание клавиатуры с кнопкой
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text="Оплатить подписку", url="https://www.ozon.ru")  # Ссылка на страницу оплаты
            markup.add(button)

            # Отправка сообщения с кнопкой
            bot.send_message(user_id, MESSAGE_TEXT, reply_markup=markup)
            logger.info(f"Напоминание с кнопкой отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")


# Планировщик задач для ежедневного уведомления в 9:00
schedule.every().day.at("12:15").do(send_subscription_reminder)


# Функция отправки приглашения подписаться на бота в канал
def send_invite_message():
    """Отправляет в канал сообщение с приглашением подписаться на бота."""
    invite_text = "🔔 Чтобы получать напоминания об оплате подписки, подпишитесь на нашего бота и нажмите /start:\n\n"
    invite_text += f"👉 [Перейти к боту](https://t.me/Uliana_posts_bot)"

    try:
        bot.send_message(CHANNEL_ID, invite_text, parse_mode="Markdown")
        logger.info("Приглашение отправлено в канал.")
    except Exception as e:
        logger.error(f"Ошибка при отправке приглашения в канал: {e}")

def run_schedule():
    while True:
        logger.info(f"Текущее время: {time.strftime('%H:%M:%S')}")
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

if __name__ == "__main__":
    init_db()
    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    bot.polling(none_stop=True)
# if __name__ == "__main__":
#     init_db()
#     # send_invite_message()  # Отправка приглашения сразу после запуска
#     bot.polling(none_stop=True)
#     while True:
#         logger.info(f"Текущее время: {time.strftime('%H:%M:%S')}")
#         schedule.run_pending()
#         time.sleep(60)
