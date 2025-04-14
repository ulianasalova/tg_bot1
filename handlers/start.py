from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db import add_user
from keyboards.main import build_main_menu
from config import Config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args  # ← получаем параметры ссылки
    username = user.username or ""

    if args:
        channel_key = args[0]
        if channel_key in Config.CHANNELS:
            from db import update_user_channel
            update_user_channel(user.id, channel_key)

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЯ бот команды SwimGlide 🏊\nВыбери, что хочешь сделать:",
        reply_markup=build_main_menu()
    )

    add_user(user.id, user.first_name, username)  # 🆕 передаём username

def get_start_handler():
    return CommandHandler(["start"], start)

