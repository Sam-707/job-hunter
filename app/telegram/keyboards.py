"""
Inline keyboard layouts for the Telegram bot.
All callback data follows the pattern: action:job_id
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def after_analysis(job_id: str, fit_score: int) -> InlineKeyboardMarkup:
    """Keyboard shown after a job is analyzed."""
    short = job_id[:8]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✉️ Anschreiben", callback_data=f"cover:{short}"),
            InlineKeyboardButton("📝 Lebenslauf-Tipps", callback_data=f"resume:{short}"),
        ],
        [
            InlineKeyboardButton("💬 Typische Fragen", callback_data=f"answers:{short}"),
            InlineKeyboardButton("✅ Checkliste", callback_data=f"checklist:{short}"),
        ],
        [
            InlineKeyboardButton("📤 Als beworben markieren", callback_data=f"applied:{short}"),
            InlineKeyboardButton("❌ Überspringen", callback_data=f"skip:{short}"),
        ],
    ])


def confirm_job_text() -> InlineKeyboardMarkup:
    """Ask user to confirm pasted text is a job description."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ja, analysieren", callback_data="confirm_text:yes"),
        InlineKeyboardButton("❌ Nein, abbrechen", callback_data="confirm_text:no"),
    ]])


def job_detail_actions(job_id: str) -> InlineKeyboardMarkup:
    """Actions for a specific job from the job list."""
    short = job_id[:8]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Analyse wiederholen", callback_data=f"reanalyze:{short}"),
            InlineKeyboardButton("✉️ Anschreiben", callback_data=f"cover:{short}"),
        ],
        [
            InlineKeyboardButton("📤 Beworben", callback_data=f"applied:{short}"),
            InlineKeyboardButton("❌ Abgelehnt", callback_data=f"rejected:{short}"),
        ],
    ])


def status_update_kb(job_id: str) -> InlineKeyboardMarkup:
    short = job_id[:8]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Beworben", callback_data=f"applied:{short}"),
            InlineKeyboardButton("💬 Im Gespräch", callback_data=f"interviewing:{short}"),
        ],
        [
            InlineKeyboardButton("✅ Angebot erhalten", callback_data=f"good_fit:{short}"),
            InlineKeyboardButton("❌ Abgelehnt", callback_data=f"rejected:{short}"),
        ],
    ])
