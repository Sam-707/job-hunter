"""
Seed script — populates a sample candidate profile and two sample jobs.
Run: python seed.py
"""
import asyncio
from app.database import init_db, AsyncSessionLocal
from app.models.profile import CandidateProfile
from app.models.job import Job


SAMPLE_PROFILE = CandidateProfile(
    id="seed-profile-001",
    name="Sam Al-Quhaif",
    email="samalquhaif@gmail.com",
    phone="0176 80259983",
    location="Berlin-Spandau, Germany",
    years_of_experience=4.0,  # Pharmacy (2017-2019) + Language school (2016-2017) + Hotel (2008-2009)
    summary=(
        "Erfahrener Büroangestellter und Kundenbetreuer mit Erfahrung in Apothekenumfeld, "
        "Sprachschule und Hotelgewerbe. Studium Wirtschaftsingenieurwesen (TU Berlin). "
        "Sehr gute Deutschkenntnisse (B2-C1), Muttersprache Arabisch, sehr gutes Englisch. "
        "Sofort verfügbar, Berlin-Spandau."
    ),
    skills=[
        "Kundenberatung", "Büroorganisation", "Terminvergabe",
        "Ablage und Dokumentation", "Telefonkontakt", "Gästeempfang",
        "Reservierungsmanagement", "MS Office", "Projektmanagement",
        "Qualitätsmanagement", "Logistik", "Controlling",
        "Kursplanung", "Teilnehmerbetreuung",
    ],
    certifications=[],
    languages=["Arabisch (Muttersprache)", "Deutsch (B2–C1)", "Englisch (sehr gut)"],
    target_roles=[
        "Bürohilfskraft", "Büroassistenz", "Sachbearbeiter",
        "Kundenbetreuer", "Verwaltungsassistenz", "Empfangsmitarbeiter",
    ],
    target_industries=[
        "Soziale Einrichtungen", "Gesundheitswesen", "Bildung",
        "Verwaltung", "Dienstleistungen",
    ],
    salary_min=0,  # Currently receiving ALG II — open to entry-level
    salary_max=0,
    salary_currency="EUR",
    work_auth_countries=["Germany"],
    work_mode_preference="onsite",  # Office/admin roles are typically onsite
    must_have=["Berlin", "Vollzeit oder Teilzeit"],
    nice_to_have=["Soziales Umfeld", "Arabischkenntnisse von Vorteil"],
    red_flags=["Vertrieb auf Provisionsbasis", "Außendienst", "MLM", "unbezahltes Praktikum"],
    is_active=True,
    notes=(
        "Berufsprofil: Bürohilfskräfte / Büroassistenz. "
        "Aktuell arbeitslos gemeldet (ALG II Berlin). Sofort verfügbar. "
        "TU Berlin Wirtschaftsingenieurwesen (ohne Abschluss, 2010–2014). "
        "CV: Sam_Al-Quhaif_Lebenslauf_CUBA_ohne_Kompetenzen.html"
    ),
)

SAMPLE_JOB_1 = Job(
    id="seed-job-001",
    input_type="text",
    input_text="See description field",
    title="Bürohilfskraft (m/w/d)",
    company="C.U.B.A. gGmbH",
    location="Berlin",
    employment_type="full-time",
    work_mode="onsite",
    description=(
        "C.U.B.A. gGmbH sucht Bürohilfskräfte (m/w/d) für allgemeine Bürotätigkeiten in Berlin. "
        "Aufgaben: Ablage, Postbearbeitung, Terminvergabe, telefonischer Kundenkontakt, "
        "Unterstützung der Sachbearbeitung. Deutschkenntnisse mindestens B2 erforderlich. "
        "Arabischkenntnisse willkommen. Sofortiger Einstieg möglich."
    ),
    requirements=[
        "Deutschkenntnisse mindestens B2",
        "Grundlegende Bürokenntnisse (MS Office)",
        "Zuverlässigkeit und Sorgfalt",
        "Teamfähigkeit",
        "Erste Erfahrung im Büro- oder Verwaltungsbereich von Vorteil",
    ],
    responsibilities=[
        "Allgemeine Bürotätigkeiten (Ablage, Post, Kopieren)",
        "Telefonkontakt und Terminvergabe",
        "Unterstützung der Sachbearbeitung",
        "Empfang und Betreuung von Besucherinnen und Besuchern",
    ],
    extraction_method="manual_text",
    extraction_confidence="high",
    status="to_review",
    profile_id="seed-profile-001",
)

SAMPLE_JOB_2 = Job(
    id="seed-job-002",
    input_type="text",
    input_text="See description field",
    title="Empfangsmitarbeiter / Rezeptionist (m/w/d)",
    company="Arabisches Kulturzentrum Berlin",
    location="Berlin-Mitte",
    employment_type="part-time",
    work_mode="onsite",
    description=(
        "Wir suchen einen Empfangsmitarbeiter (m/w/d) mit sehr guten Arabisch- und Deutschkenntnissen. "
        "Aufgaben: Gästeempfang, Terminkoordination, Telefonannahme, allgemeine Büroorganisation. "
        "Erfahrung im Front-Office-Bereich erwünscht. Teilzeit, Berlin-Mitte. "
        "Arabischkenntnisse erforderlich, Deutschkenntnisse mindestens B2."
    ),
    requirements=[
        "Arabisch als Muttersprache oder verhandlungssicher",
        "Deutschkenntnisse B2 oder besser",
        "Erfahrung im Empfang oder Büromanagement",
        "Freundliches Auftreten und Serviceorientierung",
    ],
    responsibilities=[
        "Empfang und Betreuung von Gästen und Besuchern",
        "Terminkoordination und Kalenderverwaltung",
        "Telefonannahme auf Arabisch und Deutsch",
        "Unterstützung bei Veranstaltungen",
    ],
    extraction_method="manual_text",
    extraction_confidence="high",
    status="to_review",
    profile_id="seed-profile-001",
)


async def seed():
    print("Initializing database...")
    await init_db()
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select
        existing = await db.execute(
            select(CandidateProfile).where(CandidateProfile.id == "seed-profile-001")
        )
        if existing.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        db.add(SAMPLE_PROFILE)
        await db.flush()
        db.add(SAMPLE_JOB_1)
        db.add(SAMPLE_JOB_2)
        await db.commit()
        print("Seed complete:")
        print(f"  Profil:   seed-profile-001 ({SAMPLE_PROFILE.name}, {SAMPLE_PROFILE.location})")
        print(f"  Job 1:    seed-job-001 ({SAMPLE_JOB_1.title} @ {SAMPLE_JOB_1.company})")
        print(f"  Job 2:    seed-job-002 ({SAMPLE_JOB_2.title} @ {SAMPLE_JOB_2.company})")


if __name__ == "__main__":
    asyncio.run(seed())
