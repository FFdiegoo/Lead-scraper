"""
Verrijkt een lead met eigenaarsnaam en email adres via:
  1. Hunter.io domain search  — email patroon + bekende emails voor het domein
  2. Website scraping          — Over ons / Team / Contact pagina's + mailto links
  3. Hunter.io email finder    — direct email zoeken op naam + domein
  4. DuckDuckGo LinkedIn       — eigenaar naam zoeken
  5. Email patroon guess       — naam + patroon combineren
  6. DDG web search            — last resort
"""
import re
import time
import warnings
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urljoin

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

try:
    from ddgs import DDGS
except ImportError:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from duckduckgo_search import DDGS  # type: ignore

import config
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

OWNER_TITLES_RE = re.compile(
    r"eigenaar|directeur|oprichter|ceo|founder|zaakvoerder|directeur-eigenaar|owner|managing\s+director",
    re.IGNORECASE,
)

_OWNER_PATTERNS = [
    r"(?:eigenaar|directeur|oprichter|ceo|founder|zaakvoerder|directeur-eigenaar)"
    r"[:\s\-]+([A-Z][a-zA-ZÀ-ÿ]+ (?:[a-zA-ZÀ-ÿ]{1,4} )?[A-Z][a-zA-ZÀ-ÿ]+)",
    r"([A-Z][a-zA-ZÀ-ÿ]+ (?:[a-zA-ZÀ-ÿ]{1,4} )?[A-Z][a-zA-ZÀ-ÿ]+)"
    r"\s*[\-|,]\s*(?:eigenaar|directeur|oprichter|ceo|founder|zaakvoerder)",
]

_PAGES = ["", "/over-ons", "/over", "/team", "/contact", "/about",
          "/bedrijf", "/wie-zijn-wij", "/ons-team", "/management"]


# ── Hunter.io ────────────────────────────────────────────────────────────────

def _hunter_domain_search(domain: str) -> dict:
    """
    Zoekt alle bekende emails voor een domein via Hunter.io.
    Geeft terug: patroon, lijst met emails, en de beste eigenaar-email.
    """
    if not config.HUNTER_API_KEY or not domain:
        return {}
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={
                "domain": domain,
                "api_key": config.HUNTER_API_KEY,
                "limit": 10,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json().get("data", {})
        pattern = data.get("pattern", "")
        emails = data.get("emails", [])

        # Zoek direct naar eigenaar/directeur in de Hunter resultaten
        owner_email = None
        owner_name = None
        for e in emails:
            position = (e.get("position") or "").lower()
            if any(t in position for t in ["eigenaar", "directeur", "ceo", "founder", "oprichter", "owner"]):
                owner_email = e.get("value", "")
                fn = e.get("first_name", "") or ""
                ln = e.get("last_name", "") or ""
                owner_name = f"{fn} {ln}".strip() or None
                break

        return {
            "pattern": pattern,
            "emails": [e.get("value", "") for e in emails],
            "owner_email": owner_email,
            "owner_name": owner_name,
        }
    except Exception as e:
        print(f"    [hunter-domain] Fout: {e}")
        return {}


def _hunter_email_finder(first_name: str, last_name: str, domain: str) -> str | None:
    """Zoekt het email adres van een specifiek persoon via Hunter.io."""
    if not config.HUNTER_API_KEY or not domain or not first_name or not last_name:
        return None
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": config.HUNTER_API_KEY,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", {})
        email = data.get("email", "")
        score = data.get("score", 0)
        # Alleen teruggeven als de confidence voldoende is
        if email and score >= 30:
            return email
        return None
    except Exception as e:
        print(f"    [hunter-finder] Fout: {e}")
        return None


# ── Website scraping ─────────────────────────────────────────────────────────

def _get_page(url: str) -> tuple[str, BeautifulSoup | None]:
    """Haalt een pagina op en geeft tekst + BeautifulSoup terug."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            return soup.get_text(" ", strip=True), soup
    except Exception:
        pass
    return "", None


def _extract_mailto_emails(soup: BeautifulSoup) -> list:
    """Haalt emails uit mailto: links — betrouwbaarder dan regex op tekst."""
    emails = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href[7:].split("?")[0].strip().lower()
            if email and "@" in email:
                emails.append(email)
    return emails


def _scrape_website(base_url: str) -> dict:
    """Scrapt meerdere pagina's op eigenaarsnaam, emails en patroon."""
    base = base_url.rstrip("/")
    all_text = ""
    all_emails: list = []
    pages_done = 0

    for suffix in _PAGES:
        if pages_done >= 4:
            break
        url = base + suffix
        text, soup = _get_page(url)
        if not text:
            continue

        all_text += " " + text
        all_emails += extract_all_emails(text)
        if soup:
            all_emails += _extract_mailto_emails(soup)

        pages_done += 1
        time.sleep(0.6)

    # Dedupliceer
    all_emails = list(dict.fromkeys(e.lower() for e in all_emails if "@" in e))
    personal = [e for e in all_emails if not is_generic(e)]
    generic = [e for e in all_emails if is_generic(e)]

    pattern = detect_pattern(all_emails)
    owner_name = _extract_owner_from_text(all_text)
    found_email = personal[0] if personal else (generic[0] if generic else None)

    return {
        "owner_name": owner_name,
        "email": found_email,
        "pattern": pattern,
        "personal_emails": personal,
    }


def _extract_owner_from_text(text: str) -> str | None:
    for pattern in _OWNER_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            words = name.split()
            if len(words) >= 2 and all(len(w) >= 2 for w in words) and 6 <= len(name) <= 50:
                return name
    return None


# ── LinkedIn via DDG ─────────────────────────────────────────────────────────

def _find_owner_linkedin(company_name: str) -> str | None:
    query = f'"{company_name}" eigenaar OR directeur OR oprichter site:linkedin.com/in'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            href = r.get("href", "")
            title = r.get("title", "")
            if "linkedin.com/in" in href:
                m = re.match(
                    r"^([A-Z][a-zA-ZÀ-ÿ]+(?: [a-zA-ZÀ-ÿ]{1,4})? [A-Z][a-zA-ZÀ-ÿ]+)",
                    title,
                )
                if m:
                    return m.group(1).strip()
        time.sleep(2)
    except Exception as e:
        print(f"    [linkedin] Fout: {e}")
    return None


# ── DDG email search ─────────────────────────────────────────────────────────

def _search_email_web(owner_name: str, company: str) -> str | None:
    query = f'"{owner_name}" "{company}" email'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            text = r.get("body", "") + " " + r.get("title", "")
            for email in extract_all_emails(text):
                if not is_generic(email):
                    return email
        time.sleep(2)
    except Exception:
        pass
    return None


# ── Hulpfuncties ─────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else None


def _split_name(full_name: str) -> tuple[str, str]:
    """Splits een naam in voornaam en achternaam (negeert tussenvoegsel)."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    # Tussenvoegsel overslaan (de, van, den, der, etc.)
    if len(parts) >= 3 and len(parts[-2]) <= 3:
        return parts[0], parts[-1]
    return parts[0], parts[-1]


# ── Hoofd-functie ─────────────────────────────────────────────────────────────

def enrich_lead(lead: dict) -> dict:
    company = lead.get("name", "")
    website = lead.get("website", "")
    domain = _extract_domain(website) if website else None
    notes: list = []

    owner_name = None
    owner_email = None
    email_pattern = None

    # ── Stap 1: Hunter.io domain search ──────────────────────────────────────
    if domain:
        print(f"  [1/5] Hunter.io domain search: {domain}")
        hunter = _hunter_domain_search(domain)
        if hunter.get("owner_email"):
            owner_email = hunter["owner_email"]
            owner_name = hunter.get("owner_name") or owner_name
            notes.append("Email direct via Hunter.io (eigenaar gevonden)")
        if hunter.get("pattern"):
            email_pattern = hunter["pattern"]
            notes.append(f"Email patroon via Hunter: {email_pattern}")
        elif hunter.get("emails"):
            email_pattern = detect_pattern(hunter["emails"])
            if email_pattern:
                notes.append(f"Email patroon afgeleid: {email_pattern}")

    # ── Stap 2: Website scrapen ───────────────────────────────────────────────
    if website and (not owner_name or not owner_email):
        print(f"  [2/5] Website scrapen: {website}")
        site = _scrape_website(website)
        if not owner_name and site.get("owner_name"):
            owner_name = site["owner_name"]
            notes.append("Naam gevonden op website")
        if not owner_email and site.get("email") and not is_generic(site["email"]):
            owner_email = site["email"]
            notes.append("Persoonlijk email op website")
        elif not owner_email and site.get("email"):
            notes.append("Alleen generiek email op website")
        if not email_pattern and site.get("pattern"):
            email_pattern = site["pattern"]
            notes.append(f"Email patroon op website: {email_pattern}")

    # ── Stap 3: LinkedIn via DDG (als naam nog ontbreekt) ────────────────────
    if not owner_name:
        print(f"  [3/5] LinkedIn zoeken voor: {company}")
        owner_name = _find_owner_linkedin(company)
        if owner_name:
            notes.append("Naam via LinkedIn search")

    # ── Stap 4: Hunter.io email finder (naam + domein bekend) ────────────────
    if owner_name and not owner_email and domain:
        print(f"  [4/5] Hunter.io email finder: {owner_name} @ {domain}")
        first, last = _split_name(owner_name)
        if first and last:
            found = _hunter_email_finder(first, last, domain)
            if found:
                owner_email = found
                notes.append("Email via Hunter.io finder")

    # ── Stap 5: Email guess op basis van patroon ─────────────────────────────
    if owner_name and not owner_email and domain and email_pattern:
        print(f"  [5/5] Email schatten met patroon '{email_pattern}'")
        first, last = _split_name(owner_name)
        guessed = guess_email(f"{first} {last}", domain, email_pattern)
        if guessed:
            owner_email = guessed
            notes.append(f"Email geschat ({email_pattern}) — verifieer!")

    # ── Fallback: brede web search ────────────────────────────────────────────
    if owner_name and not owner_email:
        print(f"  [6/6] Web search naar email...")
        found = _search_email_web(owner_name, company)
        if found:
            owner_email = found
            notes.append("Email via web search")

    lead["owner_name"] = owner_name or ""
    lead["owner_email"] = owner_email or ""
    lead["notes"] = "; ".join(notes) if notes else ""
    return lead
