import os
import logging
import re
import httpx
from dotenv import load_dotenv
from aiohttp import web
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Regular expression to validate IPv4 addresses
IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

async def fetch_ip_info(ip_address: str) -> dict:
    """Fetch network details from a reliable free IP API."""
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,regionName,city,timezone,isp,org,as,lat,lon,query"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise httpx.HTTPStatusError("API request failed", request=response.request, response=response)

def format_ip_response(data: dict) -> str:
    """Format the network data into a clean, readable message."""
    return (
        f"🌐 **Network Intelligence Report**\n\n"
        f"📍 **Public IP:** `{data.get('query')}`\n"
        f"🌍 **Country:** {data.get('country', 'N/A')}\n"
        f"🏛️ **Region/State:** {data.get('regionName', 'N/A')}\n"
        f"🏙️ **City:** {data.get('city', 'N/A')}\n"
        f"⏰ **Time Zone:** {data.get('timezone', 'N/A')}\n\n"
        f"🚀 **ISP:** {data.get('isp', 'N/A')}\n"
        f"🏢 **Organization:** {data.get('org', 'N/A')}\n"
        f"🔢 **ASN:** {data.get('as', 'N/A')}\n\n"
        f"🗺️ **Coordinates:** `{data.get('lat')}, {data.get('lon')}`"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with an interactive keyboard button."""
    keyboard = [
        [InlineKeyboardButton("🔍 Get My IP Address", callback_data="get_ip_instructions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "👋 Welcome to the **Network Intelligence Bot**!\n\n"
        "I can analyze public IP addresses and provide deep-dive geographical and ISP data.\n\n"
        "👉 Tap the button below to get started, or send me any public IPv4 address directly!"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display help information."""
    help_text = (
        "📖 **How to use this Bot:**\n\n"
        "1️⃣ **Analyze an IP:** Simply send any valid IPv4 address (e.g., `8.8.8.8`) directly into the chat.\n"
        "2️⃣ **Your Own IP:** Telegram masks your IP from bots for privacy. Tap the **'Get My IP Address'** button to see a quick link where you can safely copy your IP, then paste it here for a full analysis!"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline keyboard button tap interaction."""
    query = update.callback_query
    await query.answer()

    if query.data == "get_ip_instructions":
        instructions = (
            "🔒 **Telegram Privacy Shield**\n\n"
            "Telegram routes all traffic through its own servers, meaning bots cannot see your direct device IP.\n\n"
            "💡 **How to check yours:**\n"
            "1️⃣ Visit [icanhazip.com](https://icanhazip.com) to instantly see your public IP.\n"
            "2️⃣ Copy the IP address.\n"
            "3️⃣ Paste and send it to me right here to generate your full network report!"
        )
        await query.edit_message_text(text=instructions, parse_mode="Markdown", disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process text messages containing IP addresses."""
    user_text = update.message.text.strip()

    if not IP_REGEX.match(user_text):
        await update.message.reply_text(
            "❌ That doesn't look like a valid IPv4 address. Please check the format (e.g., `8.8.8.8`) and try again."
        )
        return

    status_message = await update.message.reply_text("🔄 Querying global routing tables... Please wait.")

    try:
        data = await fetch_ip_info(user_text)
        if data.get("status") == "fail":
            await status_message.edit_text(f"❌ API Error: {data.get('message', 'Failed to retrieve data.')}")
            return

        formatted_response = format_ip_response(data)
        await status_message.edit_text(formatted_response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error lookup processing for IP {user_text}: {e}")
        await status_message.edit_text("⚠️ An error occurred while connecting to the database lookup API. Please try again later.")

async def start_health_server():
    """Run a dummy HTTP server to satisfy Render's web service port binding rule."""
    async def handle(request):
        return web.Response(text="Bot running normally.")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server started on port {port}")

async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN missing from environment configuration. Exiting.")
        return

    # Start the local port binder for Render compatibility
    await start_health_server()

    # Build the Telegram Bot application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot long-polling cycle loop natively inside the async context
    logger.info("Bot execution loop initialized. Commencing long polling.")
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        # Keep the async loop alive continuously
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot application process terminated gracefully.")
