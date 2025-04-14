from config import Config

async def notify_admins(bot, text, parse_mode=None):
    for admin_id in Config.ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode=parse_mode)
        except Exception as e:
            print(f"❌ Ошибка при уведомлении админа {admin_id}: {e}")
