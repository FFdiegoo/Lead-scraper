"""Verstuurt de outreach email via Resend."""
import resend
import config


def send_outreach_email(to_email: str, owner_name: str) -> bool:
    resend.api_key = config.RESEND_API_KEY

    # Gebruik enkel de voornaam in de aanhef
    first_name = owner_name.split()[0] if owner_name and owner_name.strip() else "daar"
    body = config.EMAIL_BODY_TEMPLATE.format(first_name=first_name)

    try:
        params: resend.Emails.SendParams = {
            "from": f"{config.FROM_NAME} <{config.FROM_EMAIL}>",
            "to": [to_email],
            "subject": config.EMAIL_SUBJECT,
            "text": body,
        }
        resend.Emails.send(params)
        print(f"  ✓ Email verstuurd → {to_email}")
        return True
    except Exception as e:
        print(f"  ✗ Fout bij versturen → {to_email}: {e}")
        return False
