from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db import add_user
from keyboards.main import build_reminder_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋🏊‍♀️\nЯ бот команды SwimGlide 🏊\nБуду напоминать о необходимости внести платёж.",
        reply_markup=build_reminder_keyboard()
    )
    add_user(user.id, user.first_name)

def get_start_handler():
    return CommandHandler("start", start)
