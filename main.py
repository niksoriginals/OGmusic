import os, asyncio, aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
import yt_dlp

# --- ENV ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = Client("ultra-fast-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- YOUTUBE SEARCH ----------------
def youtube_search(query: str):
    ydl_opts = {
        "format": "bestaudio[ext=webm][abr<=64]/bestaudio/best",  # low bitrate for speed
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)["entries"][0]
        return {
            "title": info.get("title"),
            "artist": info.get("uploader"),
            "link": info["url"],
            "duration": info.get("duration"),
            "thumb": info.get("thumbnail"),
        }

# ---------------- SEND SONG ----------------
async def send_song(msg: Message, song: dict):
    await msg.chat.send_chat_action(ChatAction.UPLOAD_AUDIO)
    caption = f"🎶 {song['title']}\n👤 {song['artist']}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(song["link"]) as resp:
            if resp.status != 200:
                await msg.reply_text("⚠️ Failed to fetch audio")
                return
            data = await resp.read()
    
    await msg.reply_audio(
        audio=data,
        title=song["title"],
        performer=song["artist"],
        caption=caption,
        duration=song["duration"],
        thumbnail=song.get("thumb"),
    )

# ---------------- HANDLERS ----------------
@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text("⚡ Ultra Fast Music Bot\nUse: /music <song name>", quote=True)

@app.on_message(filters.command("music"))
async def music_handler(_, m: Message):
    if len(m.command) < 2:
        await m.reply_text("⚡ Example: /music tum hi ho", quote=True)
        return

    query = " ".join(m.command[1:])
    try:
        song = youtube_search(query)
        await send_song(m, song)
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}", quote=True)

if __name__ == "__main__":
    print("🚀 Ultra Fast Music Bot Running…")
    app.run()
