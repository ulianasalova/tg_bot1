import sqlite3
def migrate_invite_messages():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_messages (
            channel_key TEXT PRIMARY KEY,
            message_id INTEGER
        )
    """)
    conn.commit()
    conn.close()
