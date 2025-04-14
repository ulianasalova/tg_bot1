import sqlite3
from datetime import datetime, timedelta

DB_NAME = "reminder.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Таблица пользователей
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            payment_status TEXT DEFAULT 'not_paid',
            payment_date TEXT,
            previous_payment_date TEXT,
            next_reminder_date TEXT,
            channel TEXT
        )
    """)

    # 🔁 Обновим таблицу сообщений-приглашений
    c.execute("DROP TABLE IF EXISTS invite_messages")  # <-- удаляем старую
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_messages (
            channel_key TEXT PRIMARY KEY,
            message_id INTEGER
        )
    """)

    # Таблица логов (если используется)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            action TEXT,
            old_date TEXT,
            new_date TEXT,
            by_admin INTEGER
        )
    """)

    conn.commit()
    conn.close()


def add_user(user_id, name, username=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO users (id, name, username, payment_status)
        VALUES (?, ?, ?, 'not_paid')
        """,
        (user_id, name, username)
    )
    conn.commit()
    conn.close()

def mark_as_paid(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute("""
        UPDATE users
        SET payment_status = 'paid',
            payment_date = ?
        WHERE id = ?
    """, (today, user_id))
    conn.commit()
    conn.close()

from datetime import datetime

def mark_as_paid_custom(user_id: int, new_date: str, admin_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем текущую дату оплаты
    c.execute("SELECT payment_date FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    current_payment_date = row[0] if row else None

    # Обновляем в users
    c.execute("""
        UPDATE users
        SET previous_payment_date = ?,
            payment_date = ?,
            payment_status = 'paid'
        WHERE id = ?
    """, (current_payment_date, new_date, user_id))

    # Пишем в лог (в новую таблицу payment_log)
    c.execute("""
        INSERT INTO payment_log (user_id, action, old_date, new_date, by_admin, date_logged)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        'confirmed',
        current_payment_date,
        new_date,
        admin_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def postpone_reminder(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    next_day = (datetime.now() + timedelta(days=1)).isoformat()
    c.execute("UPDATE users SET next_reminder_date = ? WHERE id = ?", (next_day, user_id))
    conn.commit()
    conn.close()

def get_unpaid_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE payment_status != 'paid'")
    users = c.fetchall()
    conn.close()
    return users

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, payment_status, payment_date, next_reminder_date, channel, username 
        FROM users
    """)
    users = c.fetchall()
    conn.close()
    return users

def mark_as_unpaid(user_id: int, admin_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT payment_date FROM users WHERE id = ?", (user_id,))
    current_payment_date = c.fetchone()[0]

    c.execute("""
        UPDATE users
        SET payment_status = 'not_paid',
            previous_payment_date = payment_date,
            payment_date = NULL
        WHERE id = ?
    """, (user_id,))

    # Пишем в лог
    c.execute("""
        INSERT INTO payment_log (user_id, date_logged, action, by_admin, old_date, new_date)
        VALUES (?, ?, 'cancelled', ?, ?, NULL)
    """, (
        user_id,
        datetime.now().isoformat(),
        admin_id,
        current_payment_date
    ))

    conn.commit()
    conn.close()
def get_user_payment_log(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT date_logged, action, old_date, new_date, by_admin
        FROM payment_log
        WHERE user_id = ?
        ORDER BY date_logged DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_payment_date(user_id, payment_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET 
            previous_payment_date = payment_date,
            payment_date = ?,
            payment_status = 'paid'
        WHERE id = ?
    """, (payment_date, user_id))
    conn.commit()
    conn.close()
def update_user_channel(user_id, channel_key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET channel = ? WHERE id = ?", (channel_key, user_id))
    conn.commit()
    conn.close()

def get_user_channel(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT channel FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, payment_status, payment_date, previous_payment_date, channel, username
        FROM users WHERE id = ?
    """, (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def update_user_channel(user_id, channel_key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET channel = ?
        WHERE id = ?
    """, (channel_key, user_id))
    conn.commit()
    conn.close()

def save_invite_message_id(channel_key, message_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS invite_messages (
            channel_key TEXT PRIMARY KEY,
            message_id INTEGER
        )
    ''')

    # Заменим запись для канала
    c.execute("REPLACE INTO invite_messages (channel_key, message_id) VALUES (?, ?)", (channel_key, message_id))

    conn.commit()
    conn.close()

def load_invite_message_id(channel_key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT message_id FROM invite_messages WHERE channel_key = ?", (channel_key,))
    result = c.fetchone()

    conn.close()
    return result[0] if result else None

def get_all_users_csv():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, payment_status, payment_date, previous_payment_date, channel, username 
        FROM users
    """)
    users = c.fetchall()
    conn.close()
    return users