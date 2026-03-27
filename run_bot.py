"""
Entry point for the Telegram bot.

Run: python run_bot.py

DB init happens inside the bot's own event loop via post_init hook.
run_polling() is synchronous and manages the event loop internally.
"""
from app.utils.logging import configure_logging, get_logger
from app.telegram.bot import build_app

configure_logging()
logger = get_logger(__name__)


def main() -> None:
    logger.info("bot_starting")
    app = build_app()
    logger.info("polling_started")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
