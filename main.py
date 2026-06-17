"""
Daily scraper: bedrijven vinden, verrijken met eigenaar + email.
Voegt maximaal LEADS_PER_RUN nieuwe leads toe aan leads.xlsx.

Gebruik: .venv/Scripts/python.exe main.py
Task Scheduler: dagelijks om 08:00
"""
from storage.excel_manager import get_workbook, get_existing_companies, add_lead, save
from scraper.maps_scraper import get_all_candidates
from scraper.enricher import enrich_lead
import config


def main() -> None:
    print("=" * 50)
    print("  Full Force AI - Lead Scraper")
    print("=" * 50)
    print(f"Doel: {config.LEADS_PER_RUN} nieuwe leads toevoegen\n")

    wb = get_workbook()
    existing = get_existing_companies(wb)
    print(f"Bestaande leads in Excel: {len(existing)}\n")

    print("STAP 1: Bedrijven zoeken...")
    print("-" * 40)
    all_candidates = get_all_candidates()
    print(f"\nGevonden kandidaten totaal: {len(all_candidates)}")

    new_candidates = [
        c for c in all_candidates
        if c["name"].lower().strip() not in existing and c["name"].strip()
    ]
    print(f"Nieuw (nog niet in Excel): {len(new_candidates)}\n")

    if not new_candidates:
        print("Geen nieuwe kandidaten gevonden. Morgen opnieuw proberen.")
        return

    print("STAP 2: Eigenaar en email achterhalen...")
    print("-" * 40)

    added = 0
    for candidate in new_candidates:
        if added >= config.LEADS_PER_RUN:
            break

        print(f"\n[{added + 1}/{config.LEADS_PER_RUN}] {candidate['name']}")
        print(f"  Adres   : {candidate['address']}")
        print(f"  Telefoon: {candidate['phone'] or '-'}")
        print(f"  Website : {candidate['website'] or '-'}")

        enriched = enrich_lead(candidate)

        print(f"  Eigenaar: {enriched.get('owner_name') or '(niet gevonden)'}")
        print(f"  Email   : {enriched.get('owner_email') or '(niet gevonden)'}")
        if enriched.get("notes"):
            print(f"  Notities: {enriched['notes']}")

        add_lead(wb, enriched)
        existing.add(enriched["name"].lower().strip())
        added += 1

    save(wb)

    print("\n" + "=" * 50)
    print(f"  [OK] {added} nieuwe lead(s) toegevoegd aan leads.xlsx")
    print(f"  [!]  Review de leads eerst voordat emails worden verstuurd!")
    print(f"  [>]  Emails worden pas na {config.EMAIL_DELAY_HOURS}u verstuurd via send_emails.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
