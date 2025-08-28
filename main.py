import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import yt_dlp
import aiohttp
from io import BytesIO

# --- ENV ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client("ultra-fast-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- STREAM AUDIO ----------------
async def stream_youtube_audio(query: str):
    """
    Extract direct audio URL from YouTube without downloading full file.
    Returns info and audio URL.
    """
    loop = asyncio.get_event_loop()
    ydl_opts = {
        "format": "bestaudio[ext=webm][abr<=64]/bestaudio/best",  # low bitrate for speed
        "noplaylist": True,
        "quiet": True,
    }

    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            entry = info["entries"][0]
            # Choose best audio URL for streaming
            return entry, entry["url"]

    info, audio_url = await loop.run_in_executor(None, run_ydl)
    return info, audio_url

# ---------------- SEND AUDIO ----------------
async def send_song_stream(m: Message, query: str):
    await app.send_chat_action(m.chat.id, ChatAction.UPLOAD_AUDIO)
    try:
        info, audio_url = await stream_youtube_audio(query)
    except Exception as e:
        await m.reply_text(f"❌ Error fetching audio: {e}", quote=True)
        return

    try:
        # Stream audio with aiohttp directly into Telegram
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                if resp.status != 200:
                    await m.reply_text("⚠️ Failed to fetch audio", quote=True)
                    return
                data = BytesIO(await resp.read())
                data.name = f"{info['title']}.webm"  # Telegram needs a filename

        await m.reply_audio(
            audio=data,
            title=info.get("title"),
            performer=info.get("uploader"),
            caption=f"🎶 {info.get('title')}\n👤 {info.get('uploader')}",
            duration=info.get("duration")
        )
    except Exception as e:
        await m.reply_text(f"❌ Error sending audio: {e}", quote=True)

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
    await send_song_stream(m, query)

# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    print("🚀 Ultra Fast Music Bot Running…")
    app.run()
