"""Zoekt technische bedrijven via DuckDuckGo Maps (gratis, geen API key nodig)."""
import time
import random
from math import radians, sin, cos, sqrt, atan2
from duckduckgo_search import DDGS
import config


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = radians(float(lat2) - lat1)
    dlon = radians(float(lon2) - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _in_radius(lat, lon) -> bool:
    if lat is None or lon is None:
        return True  # geen coördinaten → niet filteren
    try:
        dist = _haversine_km(config.BREDA_COORDS[0], config.BREDA_COORDS[1], lat, lon)
        return dist <= config.SEARCH_RADIUS_KM
    except (ValueError, TypeError):
        return True


def _format_address(r: dict) -> str:
    parts = [
        r.get("street", ""),
        r.get("city", ""),
        r.get("zip", "") or r.get("postal_code", ""),
    ]
    addr = ", ".join(p for p in parts if p)
    return addr or r.get("address", "")


def _safe_int(val) -> int:
    try:
        return int(val) if val is not None else 0
    except (ValueError, TypeError):
        return 0


def search_category(category: str, city: str) -> list:
    results = []
    query = f"{category} {city}"
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.maps(
                keywords=query,
                place=f"{city}, Nederland",
                max_results=15,
            ))

        for r in raw:
            website = r.get("website", "") or ""
            # Verwijder trailing slashes zodat URLs consistent zijn
            if website:
                website = website.rstrip("/")

            results.append({
                "name": r.get("title", "").strip(),
                "address": _format_address(r),
                "phone": r.get("phone", "") or "",
                "website": website,
                "maps_url": r.get("url", "") or "",
                "rating": float(r.get("rating") or 0),
                "reviews": _safe_int(r.get("reviews")),
                "category": category,
                "lat": r.get("latitude"),
                "lon": r.get("longitude"),
            })

        # Kleine pauze om rate limiting te voorkomen
        time.sleep(random.uniform(2.0, 4.0))

    except Exception as e:
        print(f"  [maps] Fout bij '{query}': {e}")

    return results


def get_all_candidates() -> list:
    """
    Doorzoekt alle categorieën en steden, filtert op straal en minimum reviews.
    Stopt zodra we genoeg kandidaten hebben (10× het dagelijkse doel).
    """
    seen_names: set = set()
    candidates = []
    target = config.LEADS_PER_RUN * 10

    for category in config.CATEGORIES:
        for city in config.NEARBY_CITIES:
            print(f"  Zoeken: {category} in {city}...")
            results = search_category(category, city)

            for r in results:
                name_key = r["name"].lower().strip()
                if not name_key or name_key in seen_names:
                    continue

                if not _in_radius(r.get("lat"), r.get("lon")):
                    print(f"    Buiten straal: {r['name']}")
                    continue

                # Review filter: sla over als we het weten én te weinig
                reviews = r["reviews"]
                if 0 < reviews < config.MIN_REVIEWS:
                    print(f"    Te weinig reviews ({reviews}): {r['name']}")
                    continue

                seen_names.add(name_key)
                candidates.append(r)

            if len(candidates) >= target:
                return candidates

    return candidates
