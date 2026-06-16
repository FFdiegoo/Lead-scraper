"""Detecteert email-patronen op een website en genereert een educated guess voor de eigenaar."""
import re

# Generieke emails die niet persoonlijk zijn
_GENERIC_LOCALS = {
    "info", "contact", "hello", "support", "admin", "noreply", "no-reply",
    "mail", "office", "sales", "service", "hallo", "welkom", "bureau",
    "receptie", "secretariaat", "post", "online", "website", "info1",
    "team", "hr", "ict", "helpdesk", "planning", "inkoop", "verkoop",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def extract_all_emails(text: str) -> list:
    return EMAIL_RE.findall(text)


def is_generic(email: str) -> bool:
    local = email.split("@")[0].lower()
    return local in _GENERIC_LOCALS or local.startswith("no-reply") or local.startswith("noreply")


def detect_pattern(emails: list) -> str | None:
    """
    Detecteert het email-patroon op basis van gevonden persoonlijke emails.

    Geeft terug:
      "v.achternaam"         →  d.scognamiglio@bedrijf.nl
      "voornaam.achternaam"  →  diego.scognamiglio@bedrijf.nl
      "voornaam"             →  diego@bedrijf.nl
      None                   →  onbekend
    """
    personal = [e for e in emails if not is_generic(e)]
    for email in personal:
        local = email.split("@")[0].lower()
        parts = local.split(".")
        if len(parts) == 2:
            if len(parts[0]) == 1 and len(parts[1]) > 2:
                return "v.achternaam"
            if len(parts[0]) > 1 and len(parts[1]) > 2:
                return "voornaam.achternaam"
        elif len(parts) == 1 and len(local) > 2:
            return "voornaam"
    return None


def guess_email(owner_name: str, domain: str, pattern: str | None) -> str | None:
    """
    Maakt een email-gok op basis van naam + domein + patroon.
    Geeft None als er niet genoeg info is.
    """
    if not owner_name or not domain or not pattern:
        return None

    name_parts = owner_name.strip().split()
    if len(name_parts) < 2:
        return None

    first = name_parts[0].lower()
    last = name_parts[-1].lower()

    # Verwijder tussenvoegsel (de, van, den, etc.) als het er 3 zijn
    if len(name_parts) == 3 and len(name_parts[1]) <= 3:
        last = name_parts[2].lower()

    if pattern == "v.achternaam":
        return f"{first[0]}.{last}@{domain}"
    if pattern == "voornaam.achternaam":
        return f"{first}.{last}@{domain}"
    if pattern == "voornaam":
        return f"{first}@{domain}"

    return None
