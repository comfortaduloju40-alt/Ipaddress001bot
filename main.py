import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config, logger
from handlers import start_command, help_command, echo_message, error_handler

# Validate configurations immediately on initialization
Config.validate()

# Initialize the python-telegram-bot application natively without starting polling
ptb_app = Application.builder().token(Config.BOT_TOKEN).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown lifecycle of the FastAPI application,
    ensuring the Telegram bot webhook registers and cleans up properly.
    """
    # 1. Register handlers
    ptb_app.add_handler(CommandHandler("start", start_command))
    ptb_app.add_handler(CommandHandler("help", help_command))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    ptb_app.add_error_handler(error_handler)

    # 2. Initialize and start the PTB Application structure
    await ptb_app.initialize()
    await ptb_app.start()
    
    # 3. Configure the official webhook URL with Telegram
    webhook_target = f"{Config.WEBHOOK_URL}/webhook"
    logger.info(f"Setting Telegram webhook target to: {webhook_target}")
    await ptb_app.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
    
    yield  # The web server runs here while yielding execution
    
    # 4. Graceful shutdown sequences
    logger.info("Shutting down application webhooks and context...")
    await ptb_app.bot.delete_webhook()
    await ptb_app.stop()
    await ptb_app.shutdown()

# Initialize FastAPI with the lifespan context manager
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    """Endpoint for Render to track application health and deployment success."""
    return {"status": "healthy", "message": "Bot is running"}

@app.post("/webhook")
async def process_telegram_webhook(request: Request):
    """Receives JSON update vectors from Telegram routers and pushes them to PTB processing."""
    try:
        payload = await request.json()
        update = Update.de_json(data=payload, bot=ptb_app.bot)
        await ptb_app.update_queue.put(update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error handling webhook payload parsing: {e}")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
