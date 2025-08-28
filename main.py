import os
import asyncio
import yt_dlp
import tempfile
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("⚠️ Please set BOT_TOKEN environment variable")

# ---- yt-dlp download ----
def download_song(query: str, path: str):
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "default_search": "ytsearch1",
        "outtmpl": path,
        "quiet": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info:
            return info["entries"][0]
        return info

# ---- handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Ultra Fast Music Bot\nUse: /music <song name>"
    )

async def music_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚡ Song name do: /music tum hi ho")
        return

    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔎 Searching for: {query}")

    try:
        # temp file banate hai
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
            temp_path = tmp.name

        loop = asyncio.get_running_loop()
        entry = await loop.run_in_executor(None, download_song, query, temp_path)

        title = entry.get("title") or query
        uploader = entry.get("uploader") or "Unknown"
        duration = entry.get("duration") or 0

        caption = f"🎧 {title}\n👤 {uploader}\n⏱ {duration//60}:{duration%60:02d}"

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_AUDIO
        )

        # ab Telegram pe upload karo
        with open(temp_path, "rb") as f:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=f,
                title=title,
                performer=uploader,
                caption=caption
            )

        await msg.delete()
        os.remove(temp_path)

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# ---- run ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("music", music_handler))
    print("🚀 Ultra Fast Music Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
