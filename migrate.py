import sqlite3

conn = sqlite3.connect("reminder.db")
c = conn.cursor()

# Установим дату оплаты старше 30 дней
c.execute("""
    UPDATE users
    SET payment_date = '2024-02-01',
        payment_status = 'paid'
    WHERE id = ?
""", (6866615870,))

conn.commit()
conn.close()
print("✅ Дата оплаты обновлена")
