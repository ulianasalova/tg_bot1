from datetime import datetime, timedelta
import sqlite3
from config import DB_NAME
import json
from utils.storage import fetch_channels

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # --- Пользователи ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT
        )
    """)

    # --- Подписки пользователей на каналы ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_channels (
            user_id INTEGER,
            channel_key TEXT,
            payment_status TEXT DEFAULT 'not_paid',
            payment_date TEXT,
            previous_payment_date TEXT,
            next_reminder_date TEXT
        )
    """)

    # --- Каналы ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            tg_id INTEGER
        )
    """)

    # --- Администраторы ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            is_superadmin INTEGER DEFAULT 0,
            channels TEXT,  -- JSON: ["swimmasters", "amateur"]
            payment_details TEXT  -- данные для оплаты
        )
    """)

    # --- Привязка админов к каналам (опционально, если хочешь использовать отдельно) ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS channel_admins (
            admin_id INTEGER,
            channel_key TEXT
        )
    """)

    # --- Лог оплат ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS payment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            old_date TEXT,
            new_date TEXT,
            by_admin INTEGER,
            date_logged TEXT,
            channel_key TEXT
        )
    """)
    from config import Config

    # Проверка: есть ли уже записи в таблице каналов
    c.execute("SELECT COUNT(*) FROM channels")
    if c.fetchone()[0] == 0:
        for key, data in fetch_channels().items():
            c.execute("""
                INSERT INTO channels (key, title, description, tg_id)
                VALUES (?, ?, ?, ?)
            """, (
                key,
                data["title"],
                data["description"],
                data["id"]
            ))

    conn.commit()
    conn.close()


def create_indexes():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # --- users
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

    # --- user_channels
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_channels_user_id ON user_channels(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_channels_channel_key ON user_channels(channel_key);")

    # --- payment_log
    c.execute("CREATE INDEX IF NOT EXISTS idx_payment_log_user_id ON payment_log(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payment_log_channel_key ON payment_log(channel_key);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payment_log_action ON payment_log(action);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payment_log_date_logged ON payment_log(date_logged);")

    # --- admins
    c.execute("CREATE INDEX IF NOT EXISTS idx_admins_id ON admins(id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_admins_is_superadmin ON admins(is_superadmin);")

    # --- channel_admins
    c.execute("CREATE INDEX IF NOT EXISTS idx_channel_admins_admin_id ON channel_admins(admin_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_channel_admins_channel_key ON channel_admins(channel_key);")

    conn.commit()
    conn.close()

def add_user(user_id, name, username=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Добавляем пользователя (без полей оплаты)
    c.execute(
        """
        INSERT OR IGNORE INTO users (id, name, username)
        VALUES (?, ?, ?)
        """,
        (user_id, name, username)
    )

    conn.commit()
    conn.close()

from datetime import datetime, date
import sqlite3


def mark_as_paid_custom(
        user_id: int,
        channel_key: str,
        payment_date: str,
        admin_id: int = None,
        action: str = None  # 'confirmed' или None
):
    # --- 0. Приведение payment_date к ISO-формату 'YYYY-MM-DD' ---
    if isinstance(payment_date, datetime):
        payment_date = payment_date.date().isoformat()
    elif isinstance(payment_date, date):
        payment_date = payment_date.isoformat()
    elif isinstance(payment_date, str):
        payment_date = payment_date[:10]  # '2025-04-19 00:00:00' → '2025-04-19'
    else:
        raise ValueError("❌ Неверный тип payment_date")

    # --- 1. Получаем предыдущую дату оплаты (если была) ---
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT payment_date FROM user_channels
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))
    row = c.fetchone()
    previous_date = row[0] if row else None

    # Приводим previous_date к нужному формату
    if previous_date and isinstance(previous_date, str):
        previous_date = previous_date[:10]

    # --- 2. Рассчитываем дату следующего напоминания ---
    next_reminder_date = (
            datetime.fromisoformat(payment_date) + timedelta(days=27)
    ).date().isoformat()

    # --- 3. Обновляем или вставляем в user_channels ---
    if row:
        c.execute("""
            UPDATE user_channels
            SET 
                previous_payment_date = ?,
                payment_date = ?,
                next_reminder_date = ?,
                payment_status = 'paid'
            WHERE user_id = ? AND channel_key = ?
        """, (previous_date, payment_date, next_reminder_date, user_id, channel_key))
    else:
        c.execute("""
            INSERT INTO user_channels (
                user_id, channel_key, previous_payment_date, payment_date, next_reminder_date, payment_status
            ) VALUES (?, ?, ?, ?, ?, 'paid')
        """, (user_id, channel_key, previous_date, payment_date, next_reminder_date))

    # --- 4. Вставляем запись в payment_log ---
    c.execute("""
        INSERT INTO payment_log (
            user_id, channel_key, action, old_date, new_date, by_admin, date_logged
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        channel_key,
        action,
        previous_date,
        payment_date,
        admin_id,
        datetime.now().date().isoformat()  # 👈 дата лога тоже в ISO
    ))

    conn.commit()
    conn.close()



def mark_as_unpaid(user_id: int, channel_key: str, admin_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем текущую дату оплаты (если есть)
    c.execute("""
        SELECT payment_date FROM user_channels
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))
    row = c.fetchone()
    payment_date = row[0] if row else None

    # Обновляем статус в user_channels
    c.execute("""
        UPDATE user_channels
        SET 
            previous_payment_date = payment_date,
            payment_date = NULL,
            next_reminder_date = NULL,
            payment_status = 'not_paid'
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))

    # Логируем отмену
    c.execute("""
        INSERT INTO payment_log (user_id, channel_key, action, old_date, new_date, by_admin, date_logged)
        VALUES (?, ?, 'cancelled', ?, NULL, ?, ?)
    """, (
        user_id,
        channel_key,
        payment_date,
        admin_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_all_admins():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем базовую информацию об админах
    c.execute("SELECT id, name, username, is_superadmin FROM admins")
    rows = c.fetchall()

    # Получаем связи админов с каналами
    c.execute("SELECT admin_id, channel_key FROM channel_admins")
    channel_map = {}
    for admin_id, channel_key in c.fetchall():
        channel_map.setdefault(admin_id, []).append(channel_key)

    conn.close()

    # Формируем список админов с каналами
    admins = []
    for row in rows:
        admin_id = row[0]
        admins.append((
            row[0],  # id
            row[1],  # name
            row[2],  # username
            row[3],  # is_superadmin
            channel_map.get(admin_id, [])  # список каналов
        ))

    return admins

def get_admin_by_id(admin_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Добавляем payment_details в выборку
    c.execute("""
        SELECT id, name, username, is_superadmin, payment_details
        FROM admins
        WHERE id = ?
    """, (admin_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return None

    # Получаем каналы, за которые отвечает админ
    c.execute("""
        SELECT channel_key FROM channel_admins
        WHERE admin_id = ?
    """, (admin_id,))
    channels = [r[0] for r in c.fetchall()]

    conn.close()

    admin = {
        "id": row[0],
        "name": row[1],
        "username": row[2],
        "is_superadmin": bool(row[3]),
        "payment_details": row[4],  # ✅ добавляем!
        "channels": channels
    }

    return admin



from logger import logger  # добавь этот импорт вверху файла

def get_admins_for_channel(channel_key: str) -> list[int]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    logger.debug(f"Запрос админов для канала: {channel_key}")

    c.execute("""
        SELECT a.id
        FROM admins a
        JOIN channel_admins ca ON a.id = ca.admin_id
        WHERE ca.channel_key = ? AND a.is_superadmin = 0
    """, (channel_key,))

    rows = c.fetchall()
    conn.close()

    admin_ids = [row[0] for row in rows]
    logger.info(f"Найдено {len(admin_ids)} админов для канала '{channel_key}': {admin_ids}")


    return admin_ids



def is_admin(user_id: int) -> bool:
    admin = get_admin_by_id(user_id)
    return admin is not None

def is_superadmin(user_id: int) -> bool:
    admin = get_admin_by_id(user_id)
    return admin is not None and admin["is_superadmin"]

def get_superadmin_ids():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id FROM admins WHERE is_superadmin = 1")
    rows = c.fetchall()

    conn.close()
    return [row[0] for row in rows]

def get_admin_channels(user_id: int) -> list[str]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT channel_key FROM channel_admins WHERE admin_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def postpone_reminder(user_id: int, channel_key: str):
    conn = sqlite3.connect(DB_NAME)
    try:
        c = conn.cursor()
        next_day = (datetime.now() + timedelta(days=1)).date().isoformat()
        c.execute("""
            UPDATE user_channels
            SET next_reminder_date = ?
            WHERE user_id = ? AND channel_key = ?
        """, (next_day, user_id, channel_key))
        conn.commit()
    except Exception as e:
        print(f"⚠️ Ошибка при переносе напоминания для пользователя {user_id}: {e}")
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    SELECT 
        u.id,
        u.name,
        uc.payment_status,
        uc.payment_date,
        uc.next_reminder_date,
        uc.channel_key,
        c.title
    FROM users u
    JOIN user_channels uc ON u.id = uc.user_id
    JOIN channels c ON uc.channel_key = c.key
    """)

    result = c.fetchall()
    conn.close()
    return result


def get_user_payment_log(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT channel_key, date_logged, action, old_date, new_date, by_admin
        FROM payment_log
        WHERE user_id = ?
        ORDER BY date_logged DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_payment_date(user_id: int, channel_key: str, new_date: str, admin_id: int = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем текущую дату оплаты по данному каналу
    c.execute("""
        SELECT payment_date FROM user_channels
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))
    row = c.fetchone()
    old_date = row[0] if row else None

    # Обновляем дату в user_channels
    c.execute("""
        UPDATE user_channels
        SET payment_date = ?, payment_status = 'paid'
        WHERE user_id = ? AND channel_key = ?
    """, (new_date, user_id, channel_key))

    # Записываем в payment_log
    c.execute("""
        INSERT INTO payment_log (user_id, channel_key, action, old_date, new_date, by_admin, date_logged)
        VALUES (?, ?, 'manual_update', ?, ?, ?, ?)
    """, (
        user_id,
        channel_key,
        old_date,
        new_date,
        admin_id,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_user_by_id(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Получаем базовую информацию
    c.execute("""
        SELECT id, name, username FROM users WHERE id = ?
    """, (user_id,))
    user_row = c.fetchone()

    if not user_row:
        conn.close()
        return None

    user_id, name, username = user_row

    # Получаем подписки
    c.execute("""
        SELECT channel_key, payment_date, previous_payment_date
        FROM user_channels
        WHERE user_id = ?
    """, (user_id,))
    subscriptions = c.fetchall()

    conn.close()

    return {
        "id": user_id,
        "name": name,
        "username": username,
        "subscriptions": [
            {
                "channel_key": sub[0],
                "payment_date": sub[1],
                "previous_payment_date": sub[2]
            } for sub in subscriptions
        ]
    }

def add_user_channel(user_id: int, channel_key: str, start_date: str = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Если дата не передана — ставим сегодняшнюю
    if start_date is None:
        start_date = datetime.now().date().isoformat()

    # Проверим — если запись уже есть, не добавляем
    c.execute("""
        SELECT 1 FROM user_channels 
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))

    if not c.fetchone():
        c.execute("""
            INSERT INTO user_channels (user_id, channel_key, payment_date)
            VALUES (?, ?, ?)
        """, (user_id, channel_key, start_date))

    conn.commit()
    conn.close()

def get_users_by_channels(channel_keys: list[str]) -> list[tuple[int, str]]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    placeholders = ",".join("?" for _ in channel_keys)
    query = f"""
        SELECT DISTINCT u.id, u.name
        FROM users u
        JOIN user_channels uc ON u.id = uc.user_id
        WHERE uc.channel_key IN ({placeholders})
    """
    c.execute(query, channel_keys)
    results = c.fetchall()
    conn.close()
    return results

def get_paid_users_for_admin(admin_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    channels = get_admin_channels(admin_id)
    superadmin = is_superadmin(admin_id)

    if superadmin:
        c.execute("""
            SELECT uc.user_id, u.name, uc.payment_status, u.username, uc.channel_key, uc.payment_date
            FROM user_channels uc
            JOIN users u ON uc.user_id = u.id
            WHERE uc.payment_status = 'paid'
            ORDER BY uc.payment_date DESC
        """)
    else:
        placeholders = ",".join("?" for _ in channels)
        c.execute(f"""
            SELECT uc.user_id, u.name, uc.payment_status, u.username, uc.channel_key, uc.payment_date
            FROM user_channels uc
            JOIN users u ON uc.user_id = u.id
            WHERE uc.payment_status = 'paid'
              AND uc.channel_key IN ({placeholders})
            ORDER BY uc.payment_date DESC
        """, channels)

    results = c.fetchall()
    conn.close()
    return results

def get_user_channels(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT channel_key, payment_status, payment_date, previous_payment_date
        FROM user_channels
        WHERE user_id = ?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()

    return [
        {
            "channel_key": row[0],
            "payment_status": row[1],
            "payment_date": row[2],
            "previous_payment_date": row[3]
        }
        for row in rows
    ]


def get_unpaid_users_with_channels():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT u.id, u.name, uc.payment_status, u.username, uc.channel_key, uc.payment_date
        FROM users u
        JOIN user_channels uc ON u.id = uc.user_id
        WHERE uc.payment_status != 'paid'
    """)

    users = c.fetchall()
    conn.close()
    return users

def get_all_users_with_channels():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.name, u.username,
               uc.channel_key, uc.payment_status, uc.payment_date, uc.previous_payment_date
        FROM users u
        JOIN user_channels uc ON u.id = uc.user_id
    """)
    rows = c.fetchall()
    conn.close()

    return [
        {
            "user_id": row[0],
            "name": row[1],
            "username": row[2],
            "channel_key": row[3],
            "payment_status": row[4],
            "payment_date": row[5],
            "previous_payment_date": row[6],
        }
        for row in rows
    ]

def is_payment_confirmed(user_id: int, channel_key: str) -> bool:

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM payment_log
        WHERE user_id = ?
        AND channel_key = ?
        AND action = 'confirmed'
        AND by_admin IS NOT NULL
        LIMIT 1
    """, (user_id, channel_key))
    result = c.fetchone()
    conn.close()
    return result is not None


def get_users_pending_confirmation():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT 
            uc.user_id,
            u.name,
            u.username,
            uc.channel_key,
            uc.payment_date
        FROM user_channels uc
        JOIN users u ON u.id = uc.user_id
        LEFT JOIN (
            SELECT * 
            FROM payment_log
            WHERE id IN (
                SELECT MAX(id)
                FROM payment_log
                GROUP BY user_id, channel_key
            )
        ) pl ON pl.user_id = uc.user_id AND pl.channel_key = uc.channel_key
        WHERE (pl.action IS NULL)
          AND (
              uc.payment_date IS NULL 
              OR DATE(pl.new_date) != DATE(uc.payment_date)
          )
    """)

    results = c.fetchall()
    conn.close()
    return results

def get_distinct_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT u.id, u.name, u.username
        FROM users u
        JOIN user_channels uc ON u.id = uc.user_id
    """)
    users = c.fetchall()
    conn.close()
    return users  # список кортежей (user_id, name, username)

def mark_user_as_expired(user_id: int, channel_key: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_channels
        SET payment_status = 'expired'
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))
    conn.commit()
    conn.close()

def mark_user_come_back(user_id: int, channel_key: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_channels
        SET payment_status = 'come_back'
        WHERE user_id = ? AND channel_key = ?
    """, (user_id, channel_key))
    conn.commit()
    conn.close()

