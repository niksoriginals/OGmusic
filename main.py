import os
import asyncio
import uuid
import tempfile
import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")  # set karna zaroori

if not BOT_TOKEN:
    raise SystemExit("⚠️ Please set BOT_TOKEN environment variable")

# ----------------- Blocking ytdlp helpers (run in executor) -----------------
def ytdlp_extract_info(query: str):
    """Blocking: use YoutubeDL to extract info (searches YouTube)."""
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "default_search": "ytsearch1",
        "quiet": True,
        "nocheckcertificate": True,
        "skip_download": True,
        # don't write anything to disk
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # ytsearch1: ensures single best match
        return ydl.extract_info(f"ytsearch1:{query}", download=False)

def ytdlp_download_url_to_file(video_url: str, out_path: str):
    """Blocking: download best audio to specified path."""
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "nocheckcertificate": True,
        # convert/ffmpeg not forced; keep original audio container
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

# ----------------- Bot handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Superfast Music Bot (new)\nUse: /music <song name>\nExample: /music tum hi ho"
    )

async def music_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚡ Song name do: /music tum hi ho")
        return

    query = " ".join(context.args).strip()
    msg = await update.message.reply_text(f"🔎 Searching for: {query}")

    loop = asyncio.get_running_loop()

    try:
        # run blocking extract in executor
        info = await loop.run_in_executor(None, ytdlp_extract_info, query)
        entry = None
        if isinstance(info, dict) and info.get("entries"):
            entry = info["entries"][0]
        else:
            entry = info

        if not entry:
            await msg.edit_text("😕 Song nahi mila. Dusra naam try karo.")
            return

        title = entry.get("title") or query
        uploader = entry.get("uploader") or "Unknown"
        duration = entry.get("duration") or 0
        webpage_url = entry.get("webpage_url") or entry.get("url")

        # pick best audio format url from formats
        formats = entry.get("formats") or []
        best_url = None
        best_abr = 0
        for f in formats:
            if f.get("acodec") and f.get("acodec") != "none" and f.get("url"):
                abr = f.get("abr") or 0
                if abr >= best_abr:
                    best_abr = abr
                    best_url = f["url"]

        if not best_url:
            # try top-level url fallback
            best_url = entry.get("url")

        caption = f"👤 {uploader} | ⏱ {duration//60}:{duration%60:02d}\n🔗 {webpage_url}"

        # tell user we're uploading
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_AUDIO)

        # FIRST TRY: have Telegram fetch the direct audio URL (fastest)
        try:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=best_url,
                title=title,
                performer=uploader,
                caption=caption
            )
            await msg.delete()
            return
        except Exception as e_url:
            # Telegram couldn't fetch the URL directly (headers/cors/etc). Fall back to downloading then sending.
            print("Direct URL send failed:", str(e_url))

        # FALLBACK: download a temporary file and send
        tmp_dir = tempfile.gettempdir()
        tmp_name = f"music_{uuid.uuid4().hex}.m4a"
        tmp_path = os.path.join(tmp_dir, tmp_name)

        # Download in executor (blocking)
        # Prefer using the video's webpage_url for download
        download_target = webpage_url or best_url or query
        await msg.edit_text("⏬ Downloading (fallback). Thoda time lagega...")

        try:
            await loop.run_in_executor(None, ytdlp_download_url_to_file, download_target, tmp_path)
        except Exception as e_dl:
            await msg.edit_text(f"❌ Download failed: {e_dl}\nTry another name.")
            # cleanup if exists
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            return

        # check file size (avoid huge uploads)
        try:
            size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        except Exception:
            size_mb = None

        if size_mb and size_mb > 49:  # safe guard for typical bot limits
            await msg.edit_text(f"⚠️ File too big ({size_mb:.1f} MB). Sending link instead:\n{webpage_url}")
            try: os.remove(tmp_path)
            except: pass
            return

        # send downloaded file
        with open(tmp_path, "rb") as fh:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=fh,
                title=title,
                performer=uploader,
                caption=caption
            )

        # cleanup
        try:
            os.remove(tmp_path)
        except:
            pass

        await msg.delete()
        return

    except Exception as exc:
        await msg.edit_text(f"❌ Koi error aaya: {exc}\nTry again later.")
        return

# ----------------- Run -----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("music", music_handler))
    print("🚀 Superfast Music Bot running (python-telegram-bot)...")
    app.run_polling()

if __name__ == "__main__":
    main()
