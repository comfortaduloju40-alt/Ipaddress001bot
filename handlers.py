import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = update.effective_user
    logger.info(f"User {user.id} triggered /start")
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋 Welcome to your new bot. "
        f"Send me any message, and I will echo it back to you."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command."""
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot and get a greeting\n"
        "/help - Show this help message\n\n"
        "Or simply send any text message, and I will echo it back!"
    )
    await update.message.reply_text(help_text)

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echoes back incoming text messages and logs them."""
    user = update.effective_user
    text = update.message.text
    logger.info(f"Incoming message from {user.id} ({user.username}): '{text}'")
    await update.message.reply_text(text)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs errors caused by updates."""
    logger.error(msg="Exception occurred while handling an update:", exc_info=context.error)
    
    # Notify the user gracefully if it's an update event we can reply to
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "An unexpected error occurred internally. The engineering team has been notified."
        )
