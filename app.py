# app.py
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

APP_NAME = "Astroservice"

# ---------- Konfiguration aus Umgebungsvariablen ----------
SMTP_SERVER = os.getenv("SMTP_SERVER", "secure.kasserver.com")   # All-inkl: meist secure.kasserver.com
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))                   # 465 (SSL) oder 587 (STARTTLS)
SMTP_USER = os.getenv("SMTP_USER")                               # z.B. service@whereishine.com
SMTP_PASS = os.getenv("SMTP_PASS")
MAIL_FROM  = os.getenv("MAIL_FROM", SMTP_USER or "noreply@example.com")
MAIL_BCC   = os.getenv("MAIL_BCC")  # optional, kommasepariert

# ---------- FastAPI ----------
app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description="E-Mail Versand für ManyChat Intake (All-Inkl SMTP)",
)

# ---------- Schemas ----------
class Intake(BaseModel):
    mc_user_id: Optional[str] = Field(default=None, description="ManyChat subscriber id (optional)")
    first_name: Optional[str] = Field(default=None)
    birth_date: str = Field(description="Geburtsdatum, z.B. 04.07.1983")
    birth_time: Optional[str] = Field(default=None, description="Geburtszeit, z.B. 12:10")
    birth_place: Optional[str] = Field(default=None, description="Geburtsort, z.B. Linz")
    email: EmailStr = Field(description="Empfänger-Adresse für die Auswertung")

# ---------- E-Mail Helfer ----------
def render_preview_text(data: Intake) -> str:
    """
    Hier entsteht die kurze, kostenlose Vorschau.
    (Platzhalter – du kannst die Logik später beliebig ausbauen.)
    """
    name   = data.first_name or "du"
    bdate  = data.birth_date
    btime  = data.birth_time or "unbekannt"
    bplace = data.birth_place or "unbekannt"

    lines = [
        f"Hey {name},",
        "",
        "deine Kurz-Preview ist da 🔮",
        f"• Geburtsdatum: {bdate}",
        f"• Geburtszeit:  {btime}",
        f"• Geburtsort:   {bplace}",
        "",
        "✨ Liebe:    Venus-Linie → Partnerschaft & Schönheit",
        "🚀 Karriere:  Sonne-MC → Strahlkraft & Berufung",
        "💚 Gesundheit: Mond-IC → Rückzug & emotionale Tiefe",
        "",
        "Für deine ausführliche Astro-Ortsanalyse (mit Karte & Details) antworte einfach auf diese E-Mail.",
        "Liebe Grüße",
        "— whereishine / Astroservice",
    ]
    return "\n".join(lines)


def send_email_smtp(
    subject: str,
    body_text: str,
    to_email: str,
    from_email: str = MAIL_FROM,
    bcc: Optional[str] = MAIL_BCC,
) -> None:
    """
    Versand per All-Inkl SMTP.
    Nutzt Port 465 (SSL) oder 587 (STARTTLS) – abhängig von SMTP_PORT.
    """
    if not (SMTP_SERVER and SMTP_PORT and SMTP_USER and SMTP_PASS and from_email):
        raise RuntimeError(
            "SMTP-Umgebungsvariablen fehlen. Setze SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_FROM."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    if bcc:
        msg["Bcc"] = bcc
    msg.set_content(body_text)

    # SSL (465) oder STARTTLS (587)
    if SMTP_PORT == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

# ---------- Endpoints ----------
@app.get("/health", tags=["default"], summary="Health")
def health():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

@app.get("/mail/test", tags=["default"], summary="Mail Test")
def mail_test(to: EmailStr = Query(..., description="Empfänger zum Testen")):
    try:
        send_email_smtp(
            subject="✅ Astroservice SMTP-Test",
            body_text="Hallo! Diese Testmail bestätigt, dass dein SMTP auf Railway funktioniert.",
            to_email=str(to),
        )
        return {"status": "ok", "sent_to": str(to)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mail-Fehler: {e}")

@app.post("/mc/email-intake", tags=["default"], summary="Email Intake")
def email_intake(payload: Intake):
    """Wird vom ManyChat External Request aufgerufen."""
    try:
        preview = render_preview_text(payload)
        subject = "Deine persönliche Traumort‑Preview ✨"
        send_email_smtp(subject=subject, body_text=preview, to_email=str(payload.email))

        # Antwort an ManyChat – hier nur kurzes OK + Preview zurückgeben (falls du es im Flow anzeigen willst)
        return {"status": "ok", "preview": preview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verarbeitung/Versand fehlgeschlagen: {e}")
