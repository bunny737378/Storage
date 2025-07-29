import os
import logging
import requests
import base64
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# ENV variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_REPO_BRANCH", "main")

logging.basicConfig(level=logging.INFO)

# GitHub API base URL
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/public"

# Upload bytes directly to GitHub
async def upload_bytes_to_github(file_bytes, file_name):
    encoded_content = base64.b64encode(file_bytes).decode("utf-8")

    url = f"{GITHUB_API_URL}/{file_name}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "message": f"Upload {file_name} from Telegram bot",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }

    response = requests.put(url, json=data, headers=headers)
    if response.status_code in [200, 201]:
        return True, f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/public/{file_name}?raw=true"
    else:
        return False, response.json().get("message", "Upload failed")

# Handle file message
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)

    if not file:
        await update.message.reply_text("❌ No file detected.")
        return

    telegram_file = await file.get_file()
    file_name = getattr(file, "file_name", f"{file.file_unique_id}.jpg")
    file_bytes = await telegram_file.download_as_bytearray()

    await update.message.reply_text("⬆️ Uploading to GitHub...")

    success, msg = await upload_bytes_to_github(file_bytes, file_name)

    if success:
        await update.message.reply_text(f"✅ Uploaded!\n{msg}")
    else:
        await update.message.reply_text(f"❌ Failed to upload:\n{msg}")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me any file, and I'll upload it to your GitHub `public/` folder!")

# Dummy HTTP server for Render
async def dummy_server():
    async def handle(request):
        return web.Response(text="🤖 Telegram Bot is running...")

    app = web.Application()
    app.add_routes([web.get("/", handle)])

    port = int(os.environ.get("PORT", 8000))  # Render provides PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Dummy server running on port {port}")

# Main
if __name__ == "__main__":
    print("🤖 Starting Telegram Bot...")

    async def main():
        # Start dummy HTTP server
        asyncio.create_task(dummy_server())

        # Start Telegram bot
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
        print("✅ Bot is running and polling...")
        await app.run_polling()

    asyncio.run(main())