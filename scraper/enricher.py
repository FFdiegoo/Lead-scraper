"""
Verrijkt een lead met eigenaarsnaam en email adres via:
  1. Website scraping (Over ons / Team / Contact pagina's)
  2. DuckDuckGo search naar LinkedIn profiel
  3. Email patroon detectie + educated guess
  4. DuckDuckGo text search naar email adres
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from scraper.email_finder import (
    extract_all_emails,
    is_generic,
    detect_pattern,
    guess_email,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 8

# Patronen om eigenaar/directeur te herkennen in lopende tekst
_OWNER_PATTERNS = [
    # "Eigenaar: Jan de Vries"
    r"(?:eigenaar|directeur|oprichter|ceo|founder|zaakvoerder|directeur-eigenaar)"
    r"[:\s\-–]+([A-Z][a-zÀ-ÿ]+ (?:[a-zÀ-ÿ]{1,4} )?[A-Z][a-zÀ-ÿ]+)",
    # "Jan de Vries - Eigenaar"
    r"([A-Z][a-zÀ-ÿ]+ (?:[a-zÀ-ÿ]{1,4} )?[A-Z][a-zÀ-ÿ]+)"
    r"\s*[\-–|,]\s*(?:eigenaar|directeur|oprichter|ceo|founder|zaakvoerder)",
]

_SUBDOMAIN_PAGES = ["", "/over-ons", "/over", "/team", "/contact", "/about", "/bedrijf"]


def _extract_domain(url: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else None


def _get_page_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml").get_text(" ", strip=True)
    except Exception:
        pass
    return ""


def _scrape_website(base_url: str) -> dict:
    """Scrapt meerdere pagina's van de website op zoek naar eigenaar + emails."""
    base = base_url.rstrip("/")
    all_text = ""
    all_emails: list = []

    pages_tried = 0
    for suffix in _SUBDOMAIN_PAGES:
        url = base + suffix
        text = _get_page_text(url)
        if not text:
            continue

        all_text += " " + text
        all_emails += extract_all_emails(text)
        pages_tried += 1

        if pages_tried >= 3:
            break

        time.sleep(0.8)

    # Dedupliceer emails
    all_emails = list(dict.fromkeys(e.lower() for e in all_emails))
    personal_emails = [e for e in all_emails if not is_generic(e)]
    generic_emails = [e for e in all_emails if is_generic(e)]

    pattern = detect_pattern(all_emails)
    owner_name = _extract_owner_from_text(all_text)

    # Prioriteit: persoonlijk > generiek
    found_email = personal_emails[0] if personal_emails else (generic_emails[0] if generic_emails else None)

    return {
        "owner_name": owner_name,
        "email": found_email,
        "pattern": pattern,
        "personal_emails": personal_emails,
    }


def _extract_owner_from_text(text: str) -> str | None:
    for pattern in _OWNER_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if 5 <= len(name) <= 50:
                return name
    return None


def _find_owner_via_linkedin(company_name: str) -> str | None:
    """Zoekt via DDG naar het LinkedIn profiel van de eigenaar/directeur."""
    query = f'"{company_name}" eigenaar OR directeur OR oprichter site:linkedin.com/in'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            href = r.get("href", "")
            title = r.get("title", "")
            if "linkedin.com/in" in href:
                # LinkedIn titel: "Jan de Vries – Eigenaar – Bedrijfsnaam | LinkedIn"
                m = re.match(
                    r"^([A-Z][a-zÀ-ÿ]+(?: [a-zÀ-ÿ]{1,4})? [A-Z][a-zÀ-ÿ]+)",
                    title,
                )
                if m:
                    return m.group(1).strip()
        time.sleep(2)
    except Exception as e:
        print(f"    [linkedin] Fout: {e}")
    return None


def _search_email_web(owner_name: str, company_name: str) -> str | None:
    """Zoekt het email adres van de eigenaar via een brede web search."""
    query = f'"{owner_name}" "{company_name}" email'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            combined = (r.get("body", "") + " " + r.get("title", "")).lower()
            emails = extract_all_emails(combined)
            for email in emails:
                if not is_generic(email):
                    return email
        time.sleep(2)
    except Exception as e:
        print(f"    [email-search] Fout: {e}")
    return None


def enrich_lead(lead: dict) -> dict:
    """
    Voegt owner_name, owner_email en notes toe aan een lead-dict.
    Werkt in stappen; stopt zodra naam én email zijn gevonden.
    """
    company = lead.get("name", "")
    website = lead.get("website", "")
    notes: list = []

    owner_name = None
    owner_email = None
    email_pattern = None

    # ── Stap 1: Website scrapen ──────────────────────────────────────────────
    if website:
        print(f"  [1/4] Website scrapen: {website}")
        site_data = _scrape_website(website)
        owner_name = site_data.get("owner_name")
        owner_email = site_data.get("email")
        email_pattern = site_data.get("pattern")

        if owner_name:
            notes.append("Naam gevonden op website")
        if owner_email and not is_generic(owner_email):
            notes.append("Persoonlijk email op website")
        elif owner_email:
            notes.append("Alleen generiek email op website")
        if email_pattern:
            notes.append(f"Email patroon: {email_pattern}")

    # ── Stap 2: LinkedIn via DDG (als naam nog ontbreekt) ────────────────────
    if not owner_name:
        print(f"  [2/4] LinkedIn zoeken voor: {company}")
        owner_name = _find_owner_via_linkedin(company)
        if owner_name:
            notes.append("Naam via LinkedIn search")

    # ── Stap 3: Email gok op basis van patroon ───────────────────────────────
    if owner_name and not owner_email and website:
        domain = _extract_domain(website)
        if domain and email_pattern:
            print(f"  [3/4] Email schatten met patroon '{email_pattern}'...")
            guessed = guess_email(owner_name, domain, email_pattern)
            if guessed:
                owner_email = guessed
                notes.append(f"Email geschat ({email_pattern})")

    # ── Stap 4: Brede web search naar email ──────────────────────────────────
    if owner_name and not owner_email:
        print(f"  [4/4] Email zoeken via web search...")
        found = _search_email_web(owner_name, company)
        if found:
            owner_email = found
            notes.append("Email via web search")

    lead["owner_name"] = owner_name or ""
    lead["owner_email"] = owner_email or ""
    lead["notes"] = "; ".join(notes) if notes else ""
    return lead
