import sqlite3
from datetime import datetime, timedelta

DB_NAME = "reminder.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            payment_status TEXT DEFAULT 'not_paid',
            payment_date TEXT,
            next_reminder_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, name: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if c.fetchone() is None:
        next_day = (datetime.now() + timedelta(days=1)).isoformat()
        c.execute("INSERT INTO users (id, name, next_reminder_date) VALUES (?, ?, ?)",
                  (user_id, name, next_day))
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
    current_payment_date = c.fetchone()[0]

    # Обновляем в users
    c.execute("""
        UPDATE users
        SET previous_payment_date = ?,
            payment_date = ?,
            payment_status = 'paid'
        WHERE id = ?
    """, (current_payment_date, new_date, user_id))

    # Пишем в лог
    c.execute("""
        INSERT INTO payment_history (user_id, date_logged, action, by_admin, old_date, new_date)
        VALUES (?, ?, 'confirmed', ?, ?, ?)
    """, (
        user_id,
        datetime.now().isoformat(),
        admin_id,
        current_payment_date,
        new_date
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
        SELECT
            id,
            name,
            payment_status,
            payment_date,
            previous_payment_date,
            next_reminder_date
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
        INSERT INTO payment_history (user_id, date_logged, action, by_admin, old_date, new_date)
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
        FROM payment_history
        WHERE user_id = ?
        ORDER BY date_logged DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows
