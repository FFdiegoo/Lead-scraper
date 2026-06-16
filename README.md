# Full Force AI — Lead Scraper

Dagelijkse lead scraper voor technische bedrijven in de regio Breda (30km straal).  
Vindt bedrijven, zoekt de eigenaar op, achterhaal het email adres, en verstuurt na 48u automatisch een outreach mail via Resend.

---

## Wat het doet

| Stap | Wat | Wanneer |
|------|-----|---------|
| 1 | Zoek 2–5 technische bedrijven via DuckDuckGo Maps | Dagelijks 08:00 |
| 2 | Vind eigenaar via website + LinkedIn search | Idem |
| 3 | Achterhaal email via patronen + web search | Idem |
| 4 | Sla op in `leads.xlsx` (status: Nieuw) | Idem |
| — | **Jij reviewt en verwijdert slechte leads handmatig** | Binnen 48u |
| 5 | Verstuur outreach email naar goedgekeurde leads | Dagelijks 09:30 |

---

## Installatie

### 1. Vereisten
- Python 3.11+
- Git

### 2. Clone & installeer
```bash
git clone https://github.com/FFdiegoo/lead-scraper.git
cd lead-scraper
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configureer .env
```bash
cp .env.example .env
# Open .env en vul in:
#   RESEND_API_KEY=re_...   (van resend.com/api-keys)
#   FROM_EMAIL=diego@fullforceai.nl
```

### 4. Windows Task Scheduler instellen
Rechtermuisknop op `setup_scheduler.bat` → **Als administrator uitvoeren**

Dit maakt twee taken aan:
- `FFAI_LeadScraper` — dagelijks 08:00 → `main.py`
- `FFAI_EmailSender` — dagelijks 09:30 → `send_emails.py`

---

## Handmatig draaien

```bash
# Stap 1: nieuwe leads scrapen
python main.py

# Stap 2: emails versturen (na 48u + handmatige review)
python send_emails.py
```

---

## leads.xlsx kolommen

| Kolom | Beschrijving |
|-------|-------------|
| Bedrijf | Naam van het bedrijf |
| Adres | Straat, stad, postcode |
| Telefoon | Telefoonnummer |
| Website | URL |
| Maps URL | DuckDuckGo Maps link |
| Categorie | Zoekterm waarmee gevonden |
| **Status** | `Nieuw` → `Email Verstuurd` (of pas handmatig aan) |
| Naam Eigenaar | Gevonden via website of LinkedIn |
| Email Eigenaar | Gevonden of geschat op basis van patroon |
| Notities | Hoe naam/email gevonden werd |
| Toegevoegd Op | Tijdstip van scrapen |
| Email Verstuurd Op | Tijdstip van email versturen |

### Statussen
- **Nieuw** — net toegevoegd, wacht op review + 48u
- **Email Verstuurd** — automatisch ingesteld na versturen
- **Niet Geschikt** — stel handmatig in om te voorkomen dat er een email gaat

> ⚠️ Verander de status in `Niet Geschikt` om een lead te blokkeren vóórdat de email wordt verstuurd.

---

## Email timing

```
Dag 1  08:00  main.py      → lead wordt toegevoegd (status: Nieuw)
              ↓
              Jij checkt de leads in leads.xlsx
              Slechte leads → status aanpassen naar "Niet Geschikt"
              ↓
Dag 3  09:30  send_emails.py → emails worden verstuurd (48u+ verstreken)
```

---

## Hoe email adressen worden gevonden

1. **Website scrapen** — Over ons / Team / Contact pagina's
2. **Patroon detectie** — Als `j.jansen@bedrijf.nl` gevonden wordt, weten we het patroon is `v.achternaam`
3. **Email schatten** — Eigenaar "Pieter Bakker" → `p.bakker@bedrijf.nl`
4. **LinkedIn via DDG** — `"Bedrijfsnaam" eigenaar site:linkedin.com/in`
5. **Web search** — `"Naam Eigenaar" "Bedrijfsnaam" email`

> 📌 **Let op:** Email-adressen die zijn *geschat* zijn niet gegarandeerd correct. Check de notitiekolom: als er staat "Email geschat", verifieer voor het versturen.

---

## Gezochte categorieën

- installatiebedrijf
- klimaattechniek
- elektrotechniek
- productiebedrijf
- verhuurbedrijf technisch
- onderhoudsbedrijf

Regio: Breda + 30km (Tilburg, Bergen op Zoom, Roosendaal, Etten-Leur, Oosterhout, Waalwijk, ...)

---

## Privacy & AVG

Cold email B2B outreach naar zakelijke contacten is in Nederland toegestaan mits:
- Het gaat om een relevant aanbod voor de zakelijke activiteit van de ontvanger
- Er een duidelijke afmeldmogelijkheid is (voeg toe aan de email template indien gewenst)
- Je geen bijzondere persoonsgegevens verwerkt

Sla `leads.xlsx` veilig op — niet in een publieke cloud map.
