from telegram import Update
from telegram.ext import ContextTypes
from db import add_user, add_user_channel
from config import Config
from keyboards.main import build_main_menu

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    username = user.username or ""
    first_name = user.first_name or "Без имени"

    from db import get_user_by_id

    # 1. Добавляем пользователя (если новый)
    if not get_user_by_id(user.id):
        add_user(user.id, first_name, username)

    # 2. Если пользователь перешел по приглашению из канала
    if args:
        channel_key = args[0]
        if channel_key in Config.CHANNELS:
            add_user_channel(user.id, channel_key)

    # 3. Приветственное сообщение и меню
    await update.message.reply_text(
        f"Привет, {first_name}! 👋\nЯ бот команды SwimGlide 🏊\nВыбери, что хочешь сделать:",
        reply_markup=build_main_menu()
    )
