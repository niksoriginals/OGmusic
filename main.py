import os, requests, yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# ---- ENV ----
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---- SESSIONS ----
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (SuperfastMusicBot)"})

SAAVN_SEARCH = "https://saavn.dev/api/search/songs?query={q}"

app = Client("superfast-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- SAAVN ----------------
def saavn_search(query: str):
    try:
        r = session.get(SAAVN_SEARCH.format(q=requests.utils.quote(query)), timeout=(5, 10))
        data = r.json()
        results = (data.get("data") or {}).get("results") or []
        if not results: return None

        s = results[0]
        urls = s.get("downloadUrl") or []
        if not urls: return None
        url = urls[-1]["link"]

        return {
            "title": s.get("name"),
            "artist": s.get("primaryArtists") or "Unknown",
            "link": url,
            "thumb": (s.get("image") or [{}])[-1].get("link"),
            "duration": s.get("duration") or 0
        }
    except Exception:
        return None

# ---------------- YOUTUBE ----------------
def youtube_search(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
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
            "thumb": info.get("thumbnail"),
            "duration": info.get("duration")
        }

# ---------------- FAST SENDER ----------------
async def send_song(msg: Message, song: dict):
    await msg.chat.send_chat_action(ChatAction.UPLOAD_AUDIO)
    caption = f"👤 {song['artist']} | ⏱ {song['duration']//60}:{song['duration']%60:02d}"
    await msg.reply_audio(
        audio=song["link"],
        title=song["title"],
        performer=song["artist"],
        caption=caption,
        thumbnail=song.get("thumb")
    )

# ---------------- HANDLERS ----------------
@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text("⚡ Superfast Music Bot\nUse: /music <song name>\n\nExample: /music kesariya", quote=True)

@app.on_message(filters.command("music"))
async def music_handler(_, m: Message):
    if len(m.command) < 2:
        await m.reply_text("⚡ Song name do: /music tum hi ho", quote=True)
        return

    query = " ".join(m.command[1:])
    song = saavn_search(query)
    if not song:
        song = youtube_search(query)

    if not song:
        await m.reply_text("😕 Song nahi mila.", quote=True)
        return

    await send_song(m, song)

if __name__ == "__main__":
    print("🚀 Superfast Music Bot Running…")
    app.run()
