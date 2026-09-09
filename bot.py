import os
import threading
import tempfile
import requests

from flask import Flask, request, jsonify
from gradio_client import Client


# =========================================================
# KONFIGURASI
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

HF_TOKEN = os.environ["HF_TOKEN"]

SPACE = "innoai/minimax-h3-flashgen-4step"

CANVAS = "960x544 · 16:9 fast"

DURATION = 14

PORT = int(os.environ.get("PORT", "10000"))

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Wowon AI Video Bot is running!"


@app.route("/health")
def health():
    return "OK"


# =========================================================
# TELEGRAM API
# =========================================================

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def telegram_send_message(chat_id, text):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text
            },
            timeout=30
        )
    except Exception as e:
        print("Telegram message error:", e)


def telegram_send_video(chat_id, video_path):
    try:
        with open(video_path, "rb") as video_file:
            response = requests.post(
                f"{TELEGRAM_API}/sendVideo",
                data={
                    "chat_id": chat_id
                },
                files={
                    "video": (
                        "wowon_ai_video.mp4",
                        video_file,
                        "video/mp4"
                    )
                },
                timeout=300
            )

        print("Telegram video response:", response.text)

    except Exception as e:
        print("Telegram video error:", e)
        telegram_send_message(
            chat_id,
            "❌ Gagal mengirim video ke Telegram."
        )


# =========================================================
# MENCARI FILE VIDEO DARI HASIL GRADIO
# =========================================================

def find_video_path(result):
    """
    Mencari path video dari berbagai bentuk hasil
    yang mungkin dikembalikan Gradio.
    """

    if result is None:
        return None

    if isinstance(result, str):
        lower = result.lower()

        if lower.endswith((".mp4", ".webm", ".mov", ".mkv")):
            return result

        if os.path.exists(result):
            return result

    if isinstance(result, (list, tuple)):
        for item in result:
            found = find_video_path(item)

            if found:
                return found

    if isinstance(result, dict):
        for value in result.values():
            found = find_video_path(value)

            if found:
                return found

    return None


# =========================================================
# DOWNLOAD VIDEO JIKA HASILNYA URL
# =========================================================

def download_video_if_needed(video_path):
    if not video_path:
        return None

    if os.path.exists(video_path):
        return video_path

    if video_path.startswith("http://") or video_path.startswith("https://"):

        output_path = os.path.join(
            tempfile.gettempdir(),
            "wowon_video.mp4"
        )

        response = requests.get(
            video_path,
            timeout=300
        )

        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path

    return None


# =========================================================
# GENERATE VIDEO
# =========================================================

def generate_video(prompt):

    print("Menghubungkan ke Hugging Face...")

    client = Client(
        SPACE,
        token=HF_TOKEN,
        download_files=tempfile.gettempdir()
    )

    print("Mulai generate video...")
    print("Prompt:", prompt)

    result = client.predict(
        prompt=prompt,
        image=None,
        last_image=None,
        canvas=CANVAS,
        duration=DURATION,
        seed=0,
        enhance=True,
        api_name="/generate"
    )

    print("Hasil Gradio:", result)

    video_path = find_video_path(result)

    if not video_path:
        raise RuntimeError(
            "Video tidak ditemukan dalam hasil Hugging Face."
        )

    video_path = download_video_if_needed(video_path)

    if not video_path:
        raise RuntimeError(
            "Video gagal didownload."
        )

    return video_path


# =========================================================
# PROSES /VIDEO
# =========================================================

def process_video(chat_id, prompt):

    try:

        telegram_send_message(
            chat_id,
            "🎬 Sedang membuat video AI...\n\n"
            "⏱️ Durasi: 14 detik\n"
            "🤖 Model: MiniMax H3 FlashGen\n\n"
            "Mohon tunggu."
        )

        video_path = generate_video(prompt)

        telegram_send_message(
            chat_id,
            "✅ Video selesai dibuat!\n\n"
            "📤 Sedang mengirim video..."
        )

        telegram_send_video(
            chat_id,
            video_path
        )

        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception:
            pass

    except Exception as e:

        print("ERROR GENERATE:", repr(e))

        telegram_send_message(
            chat_id,
            "❌ Gagal membuat video.\n\n"
            f"Error: {str(e)[:800]}"
        )


# =========================================================
# MEMPROSES PESAN TELEGRAM
# =========================================================

def handle_update(update):

    message = update.get("message")

    if not message:
        return

    chat = message.get("chat")

    if not chat:
        return

    chat_id = chat.get("id")

    text = message.get("text", "").strip()

    if not text:
        return

    # -----------------------------------------
    # /start
    # -----------------------------------------

    if text == "/start":

        telegram_send_message(
            chat_id,
            "🤖 WOWON AI VIDEO\n\n"
            "Bot berhasil aktif!\n\n"
            "Cara menggunakan:\n"
            "/video <deskripsi video>\n\n"
            "Contoh:\n"
            "/video seekor kucing bermain di taman "
            "saat matahari terbenam, cinematic"
        )

        return

    # -----------------------------------------
    # /video
    # -----------------------------------------

    if text.startswith("/video"):

        prompt = text[6:].strip()

        if not prompt:

            telegram_send_message(
                chat_id,
                "❌ Prompt kosong.\n\n"
                "Contoh:\n"
                "/video seekor kucing bermain di taman"
            )

            return

        # Jalankan generate di thread supaya webhook
        # Telegram tidak tertahan selama proses AI.

        thread = threading.Thread(
            target=process_video,
            args=(chat_id, prompt),
            daemon=True
        )

        thread.start()

        return

    # -----------------------------------------
    # PESAN BIASA
    # -----------------------------------------

    telegram_send_message(
        chat_id,
        "Gunakan perintah:\n\n"
        "/video <deskripsi video>\n\n"
        "Contoh:\n"
        "/video seorang astronot berjalan di Mars"
    )


# =========================================================
# WEBHOOK TELEGRAM
# =========================================================

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():

    try:

        update = request.get_json(force=True)

        threading.Thread(
            target=handle_update,
            args=(update,),
            daemon=True
        ).start()

        return jsonify({
            "ok": True
        })

    except Exception as e:

        print("Webhook error:", repr(e))

        return jsonify({
            "ok": False
        }), 200


# =========================================================
# SET WEBHOOK
# =========================================================

def set_telegram_webhook():

    if not RENDER_URL:
        print(
            "RENDER_EXTERNAL_URL belum tersedia."
        )
        return

    webhook_url = (
        RENDER_URL +
        "/telegram-webhook"
    )

    print(
        "Mengatur Telegram webhook:",
        webhook_url
    )

    try:

        response = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            data={
                "url": webhook_url,
                "drop_pending_updates": True
            },
            timeout=30
        )

        print(
            "Set webhook response:",
            response.text
        )

    except Exception as e:

        print(
            "Webhook setup error:",
            repr(e)
        )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    set_telegram_webhook()

    app.run(
        host="0.0.0.0",
        port=PORT
                 )
