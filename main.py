import os
import asyncio
import aiohttp
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# ---- ENV ----
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client("super-ultra-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- GET FASTEST AUDIO ----------------
async def get_fast_url(query: str):
    ydl_opts = {
        "format": "bestaudio[abr<=48][ext=webm]/bestaudio[abr<=64]/bestaudio",  # ultra-low
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
    }
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title"),
            "artist": info.get("uploader"),
            "url": info["url"],
            "thumb": info.get("thumbnail"),
            "duration": info.get("duration")
        }

# ---------------- STREAM DIRECT ----------------
async def stream_ultra(msg: Message, song: dict):
    await msg.chat.send_chat_action(ChatAction.UPLOAD_AUDIO)

    caption = f"🎵 {song['title']}\n👤 {song['artist']} | ⏱ {song['duration']//60}:{song['duration']%60:02d}"

    async with aiohttp.ClientSession() as session:
        async with session.get(song["url"]) as resp:
            if resp.status != 200:
                await msg.reply_text("❌ Download failed.")
                return

            await msg.reply_audio(
                audio=resp.content,  # direct smallest stream
                title=song["title"],
                performer=song["artist"],
                caption=caption,
                thumb=song.get("thumb"),
                parse_mode="html"
            )

# ---------------- HANDLERS ----------------
@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text("🚀 Super Ultra-Fast Music Bot\nUse: /music <song name>", quote=True)

@app.on_message(filters.command("music"))
async def music_handler(_, m: Message):
    if len(m.command) < 2:
        await m.reply_text("⚡ Song name do: /music kesariya", quote=True)
        return

    query = " ".join(m.command[1:])
    song = await get_fast_url(query)
    if not song:
        await m.reply_text("😕 Song nahi mila.", quote=True)
        return

    await stream_ultra(m, song)

if __name__ == "__main__":
    print("🚀 Super Ultra-Fast Music Bot Running…")
    app.run()
