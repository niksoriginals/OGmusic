import os
import asyncio
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import yt_dlp

# --- ENV ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client("ultra-fast-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- YOUTUBE AUDIO DOWNLOAD ----------------
async def download_youtube_audio(query: str):
    """
    Downloads audio using yt_dlp to a temp file and returns info and file path.
    """
    loop = asyncio.get_event_loop()
    ydl_opts = {
        "format": "bestaudio[ext=webm][abr<=64]/bestaudio/best",  # Low bitrate for speed
        "noplaylist": True,
        "quiet": True,
        "outtmpl": os.path.join(tempfile.gettempdir(), "%(title)s.%(ext)s"),
    }

    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            file_path = ydl.prepare_filename(info)
            return info, file_path

    info, file_path = await loop.run_in_executor(None, run_ydl)
    return info, file_path

# ---------------- SEND AUDIO ----------------
async def send_song(m: Message, query: str):
    await app.send_chat_action(m.chat.id, ChatAction.UPLOAD_AUDIO)
    try:
        info, file_path = await download_youtube_audio(query)
    except Exception as e:
        await m.reply_text(f"❌ Error downloading audio: {e}", quote=True)
        return

    try:
        await m.reply_audio(
            audio=file_path,
            title=info.get("title"),
            performer=info.get("uploader"),
            caption=f"🎶 {info.get('title')}\n👤 {info.get('uploader')}",
            duration=info.get("duration"),
            thumb=info.get("thumbnail")
        )
    except Exception as e:
        await m.reply_text(f"❌ Error sending audio: {e}", quote=True)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ---------------- BOT COMMANDS ----------------
@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text("⚡ Ultra Fast Music Bot\nUse: /music <song name>", quote=True)

@app.on_message(filters.command("music"))
async def music_handler(_, m: Message):
    if len(m.command) < 2:
        await m.reply_text("⚡ Example: /music tum hi ho", quote=True)
        return

    query = " ".join(m.command[1:])
    await send_song(m, query)

# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    print("🚀 Ultra Fast Music Bot Running…")
    app.run()
