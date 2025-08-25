from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import smtplib
from email.mime.text import MIMEText

app = FastAPI(title="Where I Shine – Email Webhook")

# -------- Models --------
class Lead(BaseModel):
    first_name: Optional[str] = ""
    email: EmailStr
    birth_date: Optional[str] = ""
    birth_time: Optional[str] = ""
    birth_place: Optional[str] = ""

# -------- Helpers --------
def build_preview(lead: Lead) -> str:
    """Create the quick preview text that goes into the email.
    You can customize this freely later (or replace with real scoring)."""
    lines = [
        f"🎁 Danke {lead.first_name or 'du'}!",
        "Hier ist deine schnelle Traumort-Vorschau 🌍✨",
        "",
        "❤️ Liebe → Rom · Paris · Barcelona",
        "🏆 Karriere → Berlin · London · New York",
        "💚 Wohlbefinden → Lissabon · Bali · Costa Rica",
        "",
        "— Deine Angaben —",
        f"Geburtsdatum: {lead.birth_date or '–'}",
        f"Geburtszeit:  {lead.birth_time or '–'}",
        f"Geburtsort:   {lead.birth_place or '–'}",
    ]
    return "\n".join(lines)

def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise HTTPException(status_code=500, detail=f"Missing environment variable: {name}")
    return val

# -------- Routes --------
@app.get("/")
def root():
    return {"status": "ok", "service": "whereishine-email", "docs": "/docs"}

@app.post("/mc/email")
def send_email(
    lead: Lead,
    x_webhook_secret: Optional[str] = Header(None, convert_underscores=False)
):
    # Authenticate request
    webhook_secret = require_env("WEBHOOK_SECRET")
    if x_webhook_secret != webhook_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Build email content
    preview = build_preview(lead)
    msg = MIMEText(preview, "plain", "utf-8")
    from_email = require_env("FROM_EMAIL")
    from_name = os.getenv("FROM_NAME", "Where I Shine")
    msg["Subject"] = "Deine Traumort-Auswertung"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = lead.email

    # SMTP config
    smtp_host = require_env("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = require_env("SMTP_USER")
    smtp_pass = require_env("SMTP_PASS")

    # Send email via SMTP (STARTTLS on port 587)
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [lead.email], msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP error: {e}")

    # Response for ManyChat mapping (you can use 'preview' in Response Mapping)
    return {"status": "ok", "preview": preview}
