import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "diego@full-force.ai")
FROM_NAME = os.getenv("FROM_NAME", "Diego | Full Force AI")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

# Breda centrum coördinaten
BREDA_COORDS = (51.5719, 4.7683)
SEARCH_RADIUS_KM = 30

CATEGORIES = [
    "installatiebedrijf",
    "klimaattechniek",
    "elektrotechniek",
    "productiebedrijf",
    "verhuurbedrijf technisch",
    "onderhoudsbedrijf",
]

# Steden binnen 30km van Breda
NEARBY_CITIES = [
    "Breda",
    "Tilburg",
    "Bergen op Zoom",
    "Roosendaal",
    "Etten-Leur",
    "Oosterhout",
    "Waalwijk",
    "Zevenbergen",
    "Moerdijk",
    "Halderberge",
]

MIN_REVIEWS = 5
LEADS_PER_RUN = 5
LEADS_FILE = BASE_DIR / "leads.xlsx"
EMAIL_DELAY_HOURS = 48

EMAIL_SUBJECT = "Hoeveel uur verlies jij per week? | Full Force AI"

EMAIL_BODY_TEMPLATE = """Beste {first_name},

Snel vraagje, hoeveel uur verdwijnt er bij jullie per week in werk dat niks oplevert? Offertes, nabellen, uitzoeken, bijhouden. Uren die je niet kunt factureren.

Bij de meeste bedrijven die ik spreek is dat meer dan ze denken. Of niemand in het bedrijf heeft enig idee van hoeveel uren dit zijn.

Ik los dat op. Niet met een duur consult of een lang traject, maar met slimme AI die ik aanpas op hoe jullie werken. Snel, praktisch, en binnen 2 weken live.

Ik heb volgende week een paar plekken vrij. Ik hoor graag van je!

Diego Scognamiglio
www.Full-Force.AI
"""
