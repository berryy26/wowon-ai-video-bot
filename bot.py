import os
import asyncio
import threading

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==========================================
# WEB SERVER UNTUK KOYEB
# ==========================================

web = Flask(__name__)


@web.route("/")
def home():
    return "Wowon AI Video Bot is running!"


def run_web():
    port = int(os.environ.get("PORT", 8000))

    web.run(
        host="0.0.0.0",
        port=port
    )


# ==========================================
# TOKEN TELEGRAM
# ==========================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]


# ==========================================
# /START
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🤖 Wowon AI Video Bot aktif!\n\n"
        "Server berhasil berjalan di Koyeb.\n\n"
        "Ketik /test untuk mencoba."
    )


# ==========================================
# /TEST
# ==========================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "✅ BOT BERHASIL!\n\n"
        "Koyeb berhasil menjalankan bot Telegram."
    )


# ==========================================
# BOT
# ==========================================

async def main():

    application = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("test", test)
    )

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        drop_pending_updates=True
    )

    print("🤖 BOT TELEGRAM AKTIF")

    await asyncio.Event().wait()


# ==========================================
# JALANKAN WEB SERVER
# ==========================================

threading.Thread(
    target=run_web,
    daemon=True
).start()


# ==========================================
# JALANKAN BOT
# ==========================================

asyncio.run(main())
