import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("⚠️ Please set BOT_TOKEN environment variable")

# ---- superfast YouTube search ----
def quick_youtube_search(query: str):
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "default_search": "ytsearch1",   # only first best result
        "quiet": True,
        "nocheckcertificate": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            return info["entries"][0]
        return info

# ---- handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ Ultra Fast Music Bot\nUse: /music <song name>\n\nExample: /music tum hi ho"
    )

async def music_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚡ Song name do: /music tum hi ho")
        return

    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔎 Searching for: {query}")

    loop = asyncio.get_running_loop()
    try:
        entry = await loop.run_in_executor(None, quick_youtube_search, query)

        title = entry.get("title") or query
        uploader = entry.get("uploader") or "Unknown"
        duration = entry.get("duration") or 0
        url = entry.get("url") or entry.get("webpage_url")

        caption = f"👤 {uploader} | ⏱ {duration//60}:{duration%60:02d}"

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_DOCUMENT  # fast indicator
        )

        # direct link to Telegram (fastest)
        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=url,
            title=title,
            performer=uploader,
            caption=caption
        )

        await msg.delete()

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
