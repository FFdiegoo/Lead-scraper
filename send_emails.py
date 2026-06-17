"""
Daily email sender: verstuurt emails naar leads die:
  - Status "Nieuw" hebben
  - 48 uur of langer geleden zijn toegevoegd
  - Een email adres hebben

Gebruik: .venv\Scripts\python.exe send_emails.py
Task Scheduler: dagelijks om 09:30
"""
from storage.excel_manager import get_workbook, get_pending_emails, mark_email_sent, save
from outreach.email_sender import send_outreach_email
import config


def main() -> None:
    print("=" * 50)
    print("  Full Force AI - Email Verzender")
    print("=" * 50)

    if not config.RESEND_API_KEY:
        print("\n[FOUT] RESEND_API_KEY is niet ingesteld in .env")
        print("  Voeg je API key toe aan het .env bestand en probeer opnieuw.")
        return

    wb = get_workbook()
    pending = get_pending_emails(wb)

    print(f"\nLeads klaar voor email (48u verstreken, status Nieuw): {len(pending)}")

    if not pending:
        print("Geen emails te versturen vandaag.")
        return

    print()
    sent = 0
    failed = 0

    for lead in pending:
        print(f"Versturen naar: {lead['name']}")
        print(f"  Eigenaar : {lead['owner_name'] or '(geen naam)'}")
        print(f"  Email    : {lead['owner_email']}")

        success = send_outreach_email(lead["owner_email"], lead["owner_name"])

        if success:
            mark_email_sent(wb, lead["row"])
            sent += 1
        else:
            failed += 1

        print()

    save(wb)

    print("=" * 50)
    print(f"  [OK] Verstuurd : {sent}")
    if failed:
        print(f"  [X]  Mislukt  : {failed}")
    print("=" * 50)


if __name__ == "__main__":
    main()
