"""STRETCH: deliver nudges on Telegram. pip install python-telegram-bot
Get a token from @BotFather, put TELEGRAM_TOKEN and API_URL in .env,
run: python -m backend.telegram_bot   Users type: /start 12   (12 = household id)"""
import os
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

load_dotenv()
API = os.getenv("API_URL", "http://127.0.0.1:8000")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Send /start <household_id>, e.g. /start 12")
        return
    nudges = requests.get(f"{API}/nudges/{ctx.args[0]}", timeout=10).json()
    pending = [n for n in nudges if n["status"] == "pending"]
    if not pending:
        await update.message.reply_text("No pending nudges today. Thank you!")
    for n in pending:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Accept", callback_data=f"a:{n['id']}"),
                                    InlineKeyboardButton("Skip", callback_data=f"s:{n['id']}")]])
        await update.message.reply_text(n["message"], reply_markup=kb)


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    act, nid = q.data.split(":")
    r = requests.post(f"{API}/nudges/{nid}/respond", json={"accept": act == "a"}, timeout=10).json()
    await q.answer()
    await q.edit_message_text(f"{q.message.text}\n\n-> {r['status']}. Points: {r['household_points']}")


def main():
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()


if __name__ == "__main__":
    main()
