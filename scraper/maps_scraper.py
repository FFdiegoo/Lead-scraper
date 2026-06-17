"""
Zoekt technische bedrijven via twee gratis bronnen:
  1. Overpass API (OpenStreetMap) - gestructureerde bedrijfsdata, geen key nodig
  2. DuckDuckGo text search - aanvulling voor bedrijven die niet in OSM staan
"""
import time
import random
import re
import requests
from math import radians, sin, cos, sqrt, atan2

try:
    from ddgs import DDGS
except ImportError:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from duckduckgo_search import DDGS

import config

OVERPASS_ENDPOINTS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 FullForceAI-LeadScraper/1.0",
    "Accept": "application/json",
}

OSM_TAG_GROUPS = {
    "installatiebedrijf": [
        '["craft"="plumber"]',
        '["craft"="hvac"]',
    ],
    "klimaattechniek": [
        '["craft"="hvac"]',
    ],
    "elektrotechniek": [
        '["craft"="electrician"]',
        '["shop"="electrical"]',
    ],
    "productiebedrijf": [
        '["industrial"="factory"]',
        '["man_made"="works"]',
        '["craft"="metal_construction"]',
    ],
    "verhuurbedrijf technisch": [
        '["shop"="tools"]',
        '["amenity"="tool_rental"]',
    ],
    "onderhoudsbedrijf": [
        '["craft"="mechanic"]',
        '["office"="engineering"]',
    ],
}

# Domeinen die directory/aggregator sites zijn — geen echte bedrijven
_SKIP_DOMAINS = {
    # Directories & vergelijkingssites
    "goudengids", "yelp", "facebook", "linkedin", "kvk.nl",
    "telefoonboek", "tripadvisor", "wikipedia", "werkenbij",
    "installatie-bedrijven.nl", "installatiewerk.net", "bedrijfspagina",
    "mijnklusbedrijf", "alleinstallateurs", "zoekinstallateur",
    "zoekbedrijven", "bedrijvengids", "startpagina.nl",
    "thuisklussen", "klussenmarkt", "checkatrade", "werkspot",
    "homeadvisor", "trustpilot", "google.com", "bing.com",
    "marktplaats", "independer", "vakmantje", "klussite",
    "bedrijven.nl", "company.nl", "mijnbedrijfspagina",
    # Vacature/baan-sites
    "expatjobs", "xpatjobs", "indeed", "monster", "jobbird",
    "nationale-vacaturebank", "werkzoeken", "vacature", "jobs.",
    "jobscout", "jobrapido", "jooble", "glassdoor", "totaaljob",
    "intermediair", "randstad", "tempo-team", "manpower", "adecco",
    "undutchables", "werkenbijoverheid",
    # Overige ruis
    "dakdekkers.net", "klussen.nl", "aannemer.nl",
}

# Woorden die aangeven dat een DDG-resultaat geen echte bedrijfsnaam is
_FAKE_NAME_WORDS = {
    "zoeken", "vinden", "landelijk", "vergelijken", "offerte",
    "overzicht", "database", "directory", "gids", "lijst",
    "beste", "goedkoopste", "vergelijk", "reviews", "top",
}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = radians(float(lat2) - lat1)
    dlon = radians(float(lon2) - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _in_radius(lat, lon) -> bool:
    if lat is None or lon is None:
        return True
    try:
        return _haversine_km(config.BREDA_COORDS[0], config.BREDA_COORDS[1], lat, lon) <= config.SEARCH_RADIUS_KM
    except (ValueError, TypeError):
        return True


def _is_fake_company_name(name: str) -> bool:
    words = set(name.lower().split())
    return bool(words & _FAKE_NAME_WORDS) or len(name) > 60


def _is_skip_domain(url: str) -> bool:
    url_lower = url.lower()
    return any(d in url_lower for d in _SKIP_DOMAINS)


def _is_nl_postcode(postcode: str) -> bool:
    """Controleert of de postcode Nederlands is (bijv. 4701JC of 4701)."""
    return bool(re.match(r"^\d{4}\s?[A-Z]{0,2}$", postcode.strip().upper()))


def _osm_element_to_lead(el: dict, category: str) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name", "").strip()
    if not name:
        return None

    # Filter Belgische/andere buitenlandse bedrijven eruit via postcode
    postcode = tags.get("addr:postcode", "")
    country = tags.get("addr:country", "")
    if country and country.upper() not in ("NL", ""):
        return None
    if postcode and not _is_nl_postcode(postcode):
        return None

    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")

    street = tags.get("addr:street", "")
    housenr = tags.get("addr:housenumber", "")
    city = tags.get("addr:city", "") or tags.get("addr:place", "")
    postcode = tags.get("addr:postcode", "")
    address = ", ".join(p for p in [f"{street} {housenr}".strip(), city, postcode] if p)

    website = tags.get("website", "") or tags.get("contact:website", "")
    if website:
        website = website.rstrip("/")

    phone = (tags.get("phone", "") or tags.get("contact:phone", "") or tags.get("contact:mobile", ""))

    osm_id = el.get("id", "")
    maps_url = f"https://www.openstreetmap.org/node/{osm_id}" if el.get("type") == "node" else ""

    return {
        "name": name,
        "address": address,
        "phone": phone,
        "website": website,
        "maps_url": maps_url,
        "category": category,
        "lat": lat,
        "lon": lon,
        "source": "osm",
    }


def search_overpass(category: str) -> list:
    tag_filters = OSM_TAG_GROUPS.get(category, [])
    if not tag_filters:
        return []

    lat, lon = config.BREDA_COORDS
    radius = config.SEARCH_RADIUS_KM * 1000

    tag_queries = ""
    for tag in tag_filters:
        tag_queries += f'  node{tag}(around:{radius},{lat},{lon});\n'
        tag_queries += f'  way{tag}(around:{radius},{lat},{lon});\n'

    query = f"[out:json][timeout:30];\n(\n{tag_queries});\nout body center;"

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                headers=HEADERS,
                timeout=30,
            )
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                results = [_osm_element_to_lead(el, category) for el in elements]
                results = [r for r in results if r]
                time.sleep(1.5)
                return results
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"  [overpass] Fout bij '{category}' via {endpoint}: {e}")
            continue

    print(f"  [overpass] Alle endpoints gefaald voor '{category}'")
    return []


def search_ddg_text(category: str, city: str) -> list:
    results = []
    query = f"{category} {city} Nederland"
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=10))

        for r in raw:
            url = r.get("href", "") or ""
            title = r.get("title", "").strip()

            if _is_skip_domain(url):
                continue

            # Pak de eerste deel van de titel (voor | of -)
            name = re.split(r"\s*[\|\-]\s*", title)[0].strip()
            # Verwijder eventuele zoekcontext zoals "Elektricien in Breda? "
            name = re.sub(r"^[^?]+\?\s*", "", name).strip()
            # Verwijder overbodige locatie-toevoeging ("Breda", "Tilburg" etc.)
            for c in config.NEARBY_CITIES:
                name = re.sub(rf"\b{c}\b", "", name, flags=re.IGNORECASE).strip(" ,")

            if not name or len(name) < 4 or _is_fake_company_name(name):
                continue

            website = url.rstrip("/") if url else ""

            results.append({
                "name": name,
                "address": "",
                "phone": "",
                "website": website,
                "maps_url": "",
                "category": category,
                "lat": None,
                "lon": None,
                "source": "ddg",
            })

        time.sleep(random.uniform(2.0, 3.5))

    except Exception as e:
        print(f"  [ddg] Fout bij '{query}': {e}")

    return results


def get_all_candidates() -> list:
    seen_names: set = set()
    candidates = []
    target = config.LEADS_PER_RUN * 10

    # Ronde 1: Overpass API
    print("  [Bron 1] OpenStreetMap (Overpass API)...")
    for category in config.CATEGORIES:
        print(f"  Zoeken: {category}...")
        results = search_overpass(category)
        for r in results:
            name_key = r["name"].lower().strip()
            if not name_key or name_key in seen_names:
                continue
            if not _in_radius(r.get("lat"), r.get("lon")):
                continue
            seen_names.add(name_key)
            candidates.append(r)
        print(f"    -> {len(results)} gevonden uit OSM, uniek totaal: {len(candidates)}")

    # Ronde 2: DDG text search als aanvulling
    if len(candidates) < target:
        print(f"\n  [Bron 2] DuckDuckGo text search (aanvulling)...")
        for category in config.CATEGORIES:
            for city in config.NEARBY_CITIES[:5]:
                if len(candidates) >= target:
                    break
                print(f"  Zoeken: {category} in {city}...")
                results = search_ddg_text(category, city)
                for r in results:
                    name_key = r["name"].lower().strip()
                    if not name_key or name_key in seen_names:
                        continue
                    seen_names.add(name_key)
                    candidates.append(r)

    return candidates
