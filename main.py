import os
import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise SystemExit("⚠️ Please set BOT_TOKEN environment variable")

# ---- get streaming link ----
def get_direct_url(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "default_search": "ytsearch1",
        "quiet": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "url": info["url"],
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
        }

# ---- handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎶 Ultra Fast Music Bot\nUse: /music <song>")

async def music_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚡ Song name do: /music kesariya")
        return

    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔎 Searching {query}...")

    try:
        entry = get_direct_url(query)
        caption = f"🎧 {entry['title']}\n👤 {entry['uploader']}"

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.UPLOAD_AUDIO
        )

        await context.bot.send_audio(
            chat_id=update.effective_chat.id,
            audio=entry["url"],   # direct link no download
            title=entry["title"],
            performer=entry["uploader"],
            caption=caption
        )

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# ---- run ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("music", music_handler))
    print("🚀 Ultra Fast Music Bot Running…")
    app.run_polling()

if __name__ == "__main__":
    main()
