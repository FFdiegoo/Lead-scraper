import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "diego@fullforceai.nl")
FROM_NAME = os.getenv("FROM_NAME", "Diego | Full Force AI")

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

EMAIL_SUBJECT = "Samen je concurrenten voor zijn? | Full Force AI"

EMAIL_BODY_TEMPLATE = """Beste {first_name},

Ik ben Diego, oprichter van Full Force AI hier in de regio Breda. Wij zijn gespecialiseerd in snelle, functionele AI-oplossingen voor technische bedrijven.

Iedereen weet dat AI de toekomst is, maar bijna niemand in onze sector heeft de eerste stap gezet. Er is nu een race gaande. Wie als eerste slim automatiseert, slaat de concurrentie definitief uit het veld.

Gevestigde softwarebedrijven claimen jaren ervaring, maar luister naar dit: ik ben nieuw, hongerig en heb een enorme bewijsdrang. Het leveren van een topproduct is voor mijn bedrijf net zo cruciaal als voor dat van jou. Ik neem persoonlijk geen pauze totdat jouw systeem vlekkeloos draait en winst oplevert. Geen lange consultancy-trajecten, binnen 2 weken heb je je eerste live demo.

Durf je het aan om samen met mij je concurrenten voor te zijn? Stuur me een korte reply, dan sparren we binnenkort een kwartiertje over waar de directe winst ligt in jouw bedrijf.

Met vriendelijke groet,
Diego

Full Force AI
"""
