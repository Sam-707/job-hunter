"""
Format backend data into Telegram-safe messages.

Telegram MarkdownV2 is finicky — we use HTML mode instead.
Max message length is 4096 chars. Long messages are split.
"""
from __future__ import annotations
from app.models.job import Job
from app.models.analysis import JobAnalysis
from app.models.profile import CandidateProfile


MAX_LEN = 4000  # leave buffer below 4096


def profile_summary(profile: CandidateProfile) -> str:
    salary = ""
    if profile.salary_min or profile.salary_max:
        lo = f"{profile.salary_min:,}" if profile.salary_min else "?"
        hi = f"{profile.salary_max:,}" if profile.salary_max else "?"
        salary = f"\n💶 Zielgehalt: {lo}–{hi} {profile.salary_currency}"

    skills = ", ".join(profile.skills[:10]) if profile.skills else "—"
    langs = ", ".join(profile.languages) if profile.languages else "—"
    roles = ", ".join(profile.target_roles[:4]) if profile.target_roles else "—"
    must = "\n".join(f"  ✓ {m}" for m in profile.must_have) if profile.must_have else "  —"
    flags = ", ".join(profile.red_flags[:5]) if profile.red_flags else "—"

    return (
        f"<b>👤 Profil: {profile.name}</b>\n"
        f"📍 {profile.location or '—'}\n"
        f"📞 {profile.phone or '—'} · 📧 {profile.email or '—'}\n"
        f"⏳ Erfahrung: {profile.years_of_experience or '?'} Jahre\n"
        f"🌍 Sprachen: {langs}\n"
        f"🎯 Zielrollen: {roles}\n"
        f"🖥 Arbeitsweise: {profile.work_mode_preference or 'flexibel'}\n"
        f"🔧 Skills: {skills}\n"
        f"{salary}\n"
        f"\n<b>Must-Have:</b>\n{must}\n"
        f"\n🚩 Red Flags: {flags}"
    )


def job_submitted(job: Job) -> str:
    title = job.title or "Unbekannte Stelle"
    company = job.company or "Unbekanntes Unternehmen"
    loc = job.location or "—"
    mode = job.work_mode or "—"
    salary = job.salary_raw or _salary_str(job.salary_min, job.salary_max, job.salary_currency) or "—"
    conf = _conf_badge(job.extraction_confidence)
    return (
        f"<b>📋 Job gespeichert</b> {conf}\n\n"
        f"<b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {loc} · {mode}\n"
        f"💶 {salary}\n\n"
        f"<i>Analyse läuft …</i>"
    )


def analysis_result(job: Job, analysis: JobAnalysis) -> str:
    score = analysis.fit_score
    verdict = analysis.fit_verdict
    icon = _verdict_icon(score)

    lines = [
        f"{icon} <b>{score}/100 — {verdict}</b>",
        f"\n<b>📋 {job.title or 'Job'}</b> @ {job.company or '?'}",
        f"📍 {job.location or '—'} · {job.work_mode or '—'}",
    ]

    # Score breakdown
    bd = analysis.score_breakdown
    lines.append("\n<b>Bewertung:</b>")
    breakdown_labels = {
        "skills": "Skills",
        "experience": "Erfahrung",
        "must_have": "Must-Have",
        "work_mode": "Arbeitsweise",
        "location": "Standort",
        "salary": "Gehalt",
    }
    for key, label in breakdown_labels.items():
        val = bd.get(key, 0)
        bar = _mini_bar(val)
        lines.append(f"  {bar} {label}: {val}/100")

    # Red flags
    if analysis.risks_and_red_flags:
        lines.append("\n🚩 <b>Risiken:</b>")
        for r in analysis.risks_and_red_flags[:3]:
            lines.append(f"  • {r}")

    # Matching
    if analysis.matching_qualifications:
        lines.append("\n✅ <b>Passend:</b>")
        for q in analysis.matching_qualifications[:4]:
            lines.append(f"  • {q}")

    # Missing
    if analysis.missing_qualifications:
        lines.append("\n❌ <b>Fehlend:</b>")
        for q in analysis.missing_qualifications[:4]:
            lines.append(f"  • {q}")

    # Experience alignment
    if analysis.experience_alignment:
        lines.append(f"\n⏳ {analysis.experience_alignment}")

    lines.append(f"\n<i>ID: <code>{job.id[:8]}</code></i>")
    return "\n".join(lines)


def cover_letter(job: Job, analysis: JobAnalysis) -> list[str]:
    """Returns list of message chunks (split if too long)."""
    if not analysis.cover_letter_draft:
        return ["<i>Kein Anschreiben verfügbar. Stelle sicher, dass ein Anthropic API Key gesetzt ist.</i>"]

    header = (
        f"<b>✉️ Anschreiben — {job.title or 'Job'} @ {job.company or '?'}</b>\n"
        f"{'─' * 30}\n"
    )
    body = analysis.cover_letter_draft
    full = header + body
    return _split_message(full)


def resume_tips(job: Job, analysis: JobAnalysis) -> str:
    if not analysis.resume_tailoring_suggestions:
        return "<i>Keine Lebenslauf-Tipps verfügbar.</i>"
    tips = analysis.resume_tailoring_suggestions[:6]
    lines = [f"<b>📝 Lebenslauf-Optimierung für {job.title or 'diese Stelle'}</b>\n"]
    for i, tip in enumerate(tips, 1):
        lines.append(f"{i}. {tip}")
    return "\n".join(lines)


def checklist(analysis: JobAnalysis) -> str:
    items = analysis.application_checklist or []
    missing = analysis.missing_info_checklist or []
    lines = ["<b>✅ Bewerbungs-Checkliste</b>\n"]
    for item in items:
        lines.append(f"☐ {item}")
    if missing:
        lines.append("\n<b>⚠️ Noch fehlende Infos:</b>")
        for item in missing:
            lines.append(f"  • {item}")
    return "\n".join(lines) if len(lines) > 1 else "<i>Keine Checkliste verfügbar.</i>"


def job_list(jobs: list[Job]) -> str:
    if not jobs:
        return "<i>Keine Jobs gespeichert. Schick mir eine Job-URL oder -Beschreibung!</i>"

    status_icons = {
        "to_review": "🔍",
        "good_fit": "🟢",
        "applied": "📤",
        "interviewing": "💬",
        "rejected": "❌",
        "archived": "🗃",
    }
    lines = ["<b>📋 Deine Jobs</b>\n"]
    for job in jobs:
        icon = status_icons.get(job.status, "•")
        title = (job.title or "Unbekannt")[:35]
        company = (job.company or "?")[:20]
        score_str = ""
        if job.analysis:
            score_str = f" · {job.analysis.fit_score}/100"
        lines.append(f"{icon} <b>{title}</b> @ {company}{score_str}")
        lines.append(f"   <code>/job_{job.id[:8]}</code>")

    return "\n".join(lines)


def suggested_answers(job: Job, analysis: JobAnalysis) -> str:
    answers = analysis.suggested_answers or []
    if not answers:
        return "<i>Keine vorgeschlagenen Antworten verfügbar.</i>"
    lines = [f"<b>💬 Typische Fragen — {job.title or 'Job'}</b>\n"]
    for item in answers[:4]:
        q = item.get("question", "?")
        a = item.get("answer", "?")
        lines.append(f"<b>F: {q}</b>")
        lines.append(f"A: {a}\n")
    return "\n".join(lines)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _verdict_icon(score: int) -> str:
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🟡"
    if score >= 40:
        return "🟠"
    return "🔴"


def _mini_bar(val: int) -> str:
    filled = round(val / 20)  # 0-5 blocks
    return "█" * filled + "░" * (5 - filled)


def _conf_badge(conf: str | None) -> str:
    return {"high": "🟢", "medium": "🟡", "low": "🟠", "failed": "🔴"}.get(conf or "", "⚪")


def _salary_str(lo: int | None, hi: int | None, cur: str | None) -> str | None:
    if not lo and not hi:
        return None
    c = cur or ""
    if lo and hi:
        return f"{c}{lo:,}–{c}{hi:,}"
    return f"{c}{lo or hi:,}"


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_LEN:
        return [text]
    chunks = []
    while text:
        if len(text) <= MAX_LEN:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_LEN)
        if split_at == -1:
            split_at = MAX_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
