"""
All Telegram bot handlers.

Routing logic:
- /start, /help → static info
- /profile → active profile summary
- /jobs → list all tracked jobs
- /job_XXXXXXXX → short-ID lookup for a specific job
- URL in message → auto-submit + analyze
- Long text → ask for confirmation, then submit + analyze
- Inline callbacks → cover letter, resume tips, status updates, etc.
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes

from app.database import AsyncSessionLocal
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.services import profile_service, job_service, analysis_service
from app.schemas.job import JobSubmitRequest, JobStatusUpdate
from app.telegram import formatters as fmt
from app.telegram.keyboards import (
    after_analysis, confirm_job_text, job_detail_actions, status_update_kb
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
# Pending text confirmation: {chat_id: raw_text}
_pending_texts: dict[int, str] = {}


# ─── Commands ────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        profile = await profile_service.get_active_profile(db)

    name = profile.name if profile else "Kandidat"
    await update.message.reply_html(
        f"👋 Hallo, <b>{name}</b>!\n\n"
        "Ich bin dein persönlicher <b>Job Hunter Assistent</b>.\n\n"
        "<b>Was du tun kannst:</b>\n"
        "• Schick mir eine <b>Job-URL</b> → ich analysiere die Stelle\n"
        "• Füge eine <b>Jobbeschreibung</b> ein → ich bewerte den Fit\n"
        "• <code>/jobs</code> → alle gespeicherten Jobs\n"
        "• <code>/profile</code> → dein Profil\n"
        "• <code>/help</code> → alle Befehle\n\n"
        "<i>Einfach loslegen — schick mir eine Stelle!</i>"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "<b>📖 Befehle</b>\n\n"
        "/start — Willkommensseite\n"
        "/profile — Dein Kandidaten-Profil\n"
        "/jobs — Alle gespeicherten Jobs\n"
        "/help — Diese Hilfe\n\n"
        "<b>So funktioniert's:</b>\n"
        "1️⃣ Schick eine Job-URL oder füge Text ein\n"
        "2️⃣ Ich extrahiere die Daten und analysiere den Fit\n"
        "3️⃣ Du bekommst Score, Erklärung und Bewerbungsmaterialien\n"
        "4️⃣ Markiere Jobs als beworben, abgelehnt usw.\n\n"
        "<i>Kurzlink: /job_XXXXXXXX öffnet einen spezifischen Job</i>"
    )


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        profile = await profile_service.get_active_profile(db)
    if not profile:
        await update.message.reply_html(
            "⚠️ Noch kein Profil gesetzt.\n"
            "Erstelle eines über die REST API: <code>POST /api/v1/profile/</code>"
        )
        return
    await update.message.reply_html(fmt.profile_summary(profile))


async def cmd_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as db:
        jobs = await job_service.list_jobs(db, limit=20)
    await update.message.reply_html(fmt.job_list(jobs))


async def cmd_job_by_short_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /job_XXXXXXXX shortlinks."""
    text = update.message.text or ""
    match = re.match(r"/job_([a-f0-9\-]{8,})", text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("Ungültiger Job-Link.")
        return
    short = match.group(1).lower()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job)
            .options(selectinload(Job.analysis))
            .where(Job.id.startswith(short))
            .limit(1)
        )
        job = result.scalar_one_or_none()

    if not job:
        await update.message.reply_text("Job nicht gefunden.")
        return

    if job.analysis:
        await update.message.reply_html(
            fmt.analysis_result(job, job.analysis),
            reply_markup=job_detail_actions(job.id),
        )
    else:
        await update.message.reply_html(
            f"<b>{job.title or 'Job'}</b> @ {job.company or '?'}\n"
            f"Status: {job.status} · Noch keine Analyse.\n\n"
            f"Tippe /job_{job.id[:8]} zum Anzeigen oder starte eine Analyse.",
            reply_markup=job_detail_actions(job.id),
        )


# ─── Message handler ─────────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Route any text message — URL detection or job description prompt."""
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    if not text:
        return

    # URL detected → auto-submit
    url_match = URL_RE.search(text)
    if url_match:
        url = url_match.group(0).rstrip(".,)>")
        await _submit_and_analyze(update, ctx, url=url)
        return

    # Long text → ask for confirmation
    if len(text) >= 100:
        _pending_texts[chat_id] = text
        await update.message.reply_html(
            f"📄 Das sieht wie eine Jobbeschreibung aus ({len(text)} Zeichen).\n"
            "Soll ich diese analysieren?",
            reply_markup=confirm_job_text(),
        )
        return

    await update.message.reply_html(
        "📎 Schick mir eine <b>Job-URL</b> oder füge eine <b>Jobbeschreibung</b> (mind. 100 Zeichen) ein.\n"
        "/help für alle Befehle."
    )


# ─── Callback handler ────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    chat_id = update.effective_chat.id

    # Confirm text submission
    if data == "confirm_text:yes":
        text = _pending_texts.pop(chat_id, None)
        if not text:
            await query.edit_message_text("⚠️ Text nicht mehr verfügbar. Bitte erneut einsenden.")
            return
        await query.edit_message_text("⏳ Analysiere …")
        await _submit_and_analyze(update, ctx, text=text, edit_message=query)
        return

    if data == "confirm_text:no":
        _pending_texts.pop(chat_id, None)
        await query.edit_message_text("OK, abgebrochen.")
        return

    # All other callbacks: action:short_id
    if ":" not in data:
        return
    action, short = data.split(":", 1)

    job = await _get_job_by_short(short)
    if not job:
        await query.edit_message_text("⚠️ Job nicht gefunden.")
        return

    if action == "cover":
        chunks = fmt.cover_letter(job, job.analysis) if job.analysis else ["Keine Analyse vorhanden."]
        await query.edit_message_text(chunks[0], parse_mode=ParseMode.HTML)
        for chunk in chunks[1:]:
            await query.message.reply_html(chunk)

    elif action == "resume":
        text = fmt.resume_tips(job, job.analysis) if job.analysis else "Keine Analyse vorhanden."
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

    elif action == "answers":
        text = fmt.suggested_answers(job, job.analysis) if job.analysis else "Keine Analyse vorhanden."
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

    elif action == "checklist":
        text = fmt.checklist(job.analysis) if job.analysis else "Keine Analyse vorhanden."
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

    elif action in ("applied", "rejected", "interviewing", "good_fit", "skip"):
        status_map = {
            "applied": "applied",
            "rejected": "rejected",
            "interviewing": "interviewing",
            "good_fit": "good_fit",
            "skip": "archived",
        }
        new_status = status_map[action]
        async with AsyncSessionLocal() as db:
            await job_service.update_job_status(
                db, job.id, JobStatusUpdate(status=new_status)
            )
        status_labels = {
            "applied": "📤 Als beworben markiert",
            "rejected": "❌ Als abgelehnt markiert",
            "interviewing": "💬 Im Gespräch",
            "good_fit": "✅ Angebot / Good Fit",
            "archived": "🗃 Archiviert",
        }
        await query.edit_message_text(
            f"{status_labels.get(new_status, '✅ Status aktualisiert')}\n"
            f"<b>{job.title or 'Job'}</b> @ {job.company or '?'}",
            parse_mode=ParseMode.HTML,
        )

    elif action == "reanalyze":
        await query.edit_message_text("🔄 Analyse wird wiederholt …")
        async with AsyncSessionLocal() as db:
            profile = await profile_service.get_active_profile(db)
            if not profile:
                await query.edit_message_text("⚠️ Kein aktives Profil gefunden.")
                return
            fresh_job = await job_service.get_job(db, job.id)
            analysis = await analysis_service.run_analysis(db, fresh_job, profile)
            fresh_job = await job_service.get_job(db, job.id)

        await query.edit_message_text(
            fmt.analysis_result(fresh_job, analysis),
            parse_mode=ParseMode.HTML,
            reply_markup=after_analysis(job.id, analysis.fit_score),
        )


# ─── Core: submit + analyze ──────────────────────────────────────────────────

async def _submit_and_analyze(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    *,
    url: str | None = None,
    text: str | None = None,
    edit_message=None,
) -> None:
    """Submit a job and run analysis. Sends progress messages."""
    chat = update.effective_chat

    async def send(msg: str, **kwargs):
        if edit_message:
            try:
                await edit_message.edit_text(msg, parse_mode=ParseMode.HTML, **kwargs)
                return
            except Exception:
                pass
        await ctx.bot.send_message(chat.id, msg, parse_mode=ParseMode.HTML, **kwargs)

    await ctx.bot.send_chat_action(chat.id, ChatAction.TYPING)

    async with AsyncSessionLocal() as db:
        # Resolve profile
        profile = await profile_service.get_active_profile(db)
        if not profile:
            await send("⚠️ Kein aktives Profil. Erstelle eines über <code>POST /api/v1/profile/</code>")
            return

        # Submit job
        try:
            if url:
                await send(f"🔍 Lade Job-URL …\n<code>{url[:60]}</code>")
            req = JobSubmitRequest(url=url, text=text, profile_id=profile.id, run_analysis=False)
            job = await job_service.submit_job(db, req)
        except Exception as e:
            logger.error("telegram_submit_failed", error=str(e))
            await send(f"❌ Konnte Job nicht laden: {str(e)[:100]}")
            return

        # Show extracted data while analysis runs
        await send(fmt.job_submitted(job))
        await ctx.bot.send_chat_action(chat.id, ChatAction.TYPING)

        # Run analysis
        try:
            analysis = await analysis_service.run_analysis(db, job, profile)
        except Exception as e:
            logger.error("telegram_analysis_failed", job_id=job.id, error=str(e))
            await ctx.bot.send_message(
                chat.id,
                f"⚠️ Analyse fehlgeschlagen: {str(e)[:100]}\n"
                f"Job gespeichert als <code>/job_{job.id[:8]}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        # Fetch with relationships
        job = await job_service.get_job(db, job.id)

    await ctx.bot.send_message(
        chat.id,
        fmt.analysis_result(job, analysis),
        parse_mode=ParseMode.HTML,
        reply_markup=after_analysis(job.id, analysis.fit_score),
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_job_by_short(short: str) -> Job | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job)
            .options(selectinload(Job.analysis))
            .where(Job.id.startswith(short))
            .limit(1)
        )
        return result.scalar_one_or_none()
