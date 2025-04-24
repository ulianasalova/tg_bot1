import sqlite3
from config import DB_NAME

def fetch_channels():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT key, title, description, tg_id FROM channels")
    rows = c.fetchall()
    conn.close()

    return {
        key: {
            "id": tg_id,
            "title": title,
            "description": description
        }
        for key, title, description, tg_id in rows
    }