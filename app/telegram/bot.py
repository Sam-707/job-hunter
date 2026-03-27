"""
Telegram bot setup and registration.
Builds the Application and wires all handlers.
"""
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.config import get_settings
from app.database import init_db
from app.telegram.handlers import (
    cmd_start,
    cmd_help,
    cmd_profile,
    cmd_jobs,
    cmd_job_by_short_id,
    handle_message,
    handle_callback,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def _post_init(application: Application) -> None:
    """Runs inside the bot's own event loop before polling starts."""
    await init_db()
    logger.info("database_ready")


def build_app() -> Application:
    settings = get_settings()
    token = settings.telegram_bot_token

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("jobs", cmd_jobs))

    # Short-ID job links: /job_XXXXXXXX
    app.add_handler(
        MessageHandler(filters.Regex(r"^/job_[a-f0-9\-]{8,}"), cmd_job_by_short_id)
    )

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # All other text messages (URLs, job descriptions)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("telegram_bot_ready")
    return app
