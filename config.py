import os
import logging

# Configure logging format globally
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Config:
    """Central configuration class loaded from environment variables."""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    # Render automatically sets PORT. Default to 8000 for local testing.
    PORT = int(os.getenv("PORT", 8000)) 

    @classmethod
    def validate(cls):
        """Validates that all critical configurations are present."""
        missing = []
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not cls.WEBHOOK_URL:
            missing.append("WEBHOOK_URL")
            
        if missing:
            critical_error = f"Missing required environment variables: {', '.join(missing)}"
            logger.critical(critical_error)
            raise ValueError(critical_error)
