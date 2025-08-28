import os
import math
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# ---- Environment (Railway) ----
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---- HTTP session (fast + retries) ----
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=3)
session.mount("http://", adapter)
session.mount("https://", adapter)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SuperfastMusicBot/1.0)",
    "Accept": "application/json, */*;q=0.8",
}

SAAVN_SEARCH = "https://saavn.dev/api/search/songs?query={q}"
TIMEOUT = (5, 15)  # (connect, read)

app = Client("superfast-music", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def _best_download_url(song: dict) -> str | None:
    """
    Saavn returns an array of quality variants in 'downloadUrl'.
    We'll take the highest quality available (usually the last item).
    """
    urls = song.get("downloadUrl") or []
    if not urls:
        return None
    # Prefer highest quality by bitrate if available
    try:
        urls_sorted = sorted(urls, key=lambda x: int(x.get("quality", "0").replace("kbps","").strip()))
        return urls_sorted[-1]["link"]
    except Exception:
        return urls[-1].get("link")

def _filesize_str(bytes_val: int | None) -> str:
    if not bytes_val or bytes_val <= 0:
        return ""
    units = ["B","KB","MB","GB","TB"]
    i = int(math.floor(math.log(bytes_val,1024))) if bytes_val>0 else 0
    return f"{bytes_val / (1024**i):.1f} {units[i]}"

def search_saavn_best(query: str) -> dict | None:
    """
    Returns {title, artist, link, thumb, duration, size_bytes} or None
    """
    r = session.get(SAAVN_SEARCH.format(q=requests.utils.quote(query)), headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    data = r.json()
    results = (data.get("data") or {}).get("results") or []
    if not results:
        return None

    # Take the very first (best) match
    s = results[0]
    link = _best_download_url(s)
    if not link:
        return None

    # HEAD check for speed/size validation (no content download)
    try:
        head = session.head(link, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        size = int(head.headers.get("Content-Length", "0")) if head.ok else 0
    except Exception:
        size = 0

    return {
        "title": s.get("name") or "Unknown Title",
        "artist": s.get("primaryArtists") or s.get("artists", {}).get("primary", [{}])[0].get("name", "Unknown"),
        "link": link,
        "thumb": (s.get("image") or [{}])[-1].get("link") if s.get("image") else None,
        "duration": s.get("duration") or 0,
        "size_bytes": size
    }

async def send_audio_fast(msg: Message, song: dict):
    """Send by URL directly (Telegram fetches from source) — fastest path."""
    await msg.chat.send_chat_action(ChatAction.UPLOAD_AUDIO)
    caption_bits = []
    if song.get("artist"): caption_bits.append(f"👤 {song['artist']}")
    if song.get("duration"): caption_bits.append(f"⏱️ {int(song['duration'])//60}:{int(song['duration'])%60:02d}")
    if song.get("size_bytes"): caption_bits.append(f"💾 {_filesize_str(song['size_bytes'])}")
    caption = " | ".join(caption_bits) if caption_bits else None

    # Telegram can stream URL directly; provide metadata for nicer UI
    await msg.reply_audio(
        audio=song["link"],
        title=song["title"],
        performer=song.get("artist"),
        caption=caption,
        thumbnail=song.get("thumb")
    )

@app.on_message(filters.command(["start", "help"]))
async def start(_, m: Message):
    await m.reply_text(
        "⚡ Superfast Music Bot\n"
        "Send: /music <song name>\n\n"
        "Example: /music kesariya",
        quote=True
    )


@app.on_message(filters.command("music"))
async def music_handler(_, m: Message):
    if len(m.command) < 2:
        await m.reply_text("⚡ Song name do bhai: /music tum hi ho", quote=True)
        return

    query = " ".join(m.command[1:]).strip()
    t0 = time.time()
    try:
        song = search_saavn_best(query)
    except Exception as e:
        await m.reply_text(f"❌ Source error: {e}", quote=True)
        return

    if not song:
        await m.reply_text("😕 Song nahi mila. Dusra naam try karo.", quote=True)
        return

    try:
        await send_audio_fast(m, song)
        t1 = time.time()
        if t1 - t0 > 6:
            # Soft hint if network slow — doesn't block
            await m.reply_text("⚠️ Network thoda slow tha, par gaana bhej diya 🙂", quote=True)
    except Exception as e:
        # If direct URL fails (rare), fallback: simple redirect follow and try again once.
        try:
            # Attempt one GET to resolve any weird redirect CDNs
            r = session.get(song["link"], headers=DEFAULT_HEADERS, timeout=(5, 30), stream=True)
            final_url = r.url
            r.close()
            await m.reply_audio(
                audio=final_url,
                title=song["title"],
                performer=song.get("artist"),
                caption=None,
                thumbnail=song.get("thumb")
            )
        except Exception as e2:
            await m.reply_text(f"❌ Send failed: {e2}", quote=True)

if name == "main":
    print("🚀 Superfast Single-Song Music Bot is running…")
    app.run()
