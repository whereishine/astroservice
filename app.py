import os
import ssl
import smtplib
import socket
import logging
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from email.message import EmailMessage

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("astroservice")

# ------------------------------------------------------------------
# Konfiguration aus ENV
# ------------------------------------------------------------------
SMTP_SERVER    = os.getenv("SMTP_SERVER", "secure.kasserver.com").strip()
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER      = os.getenv("SMTP_USER", "").strip()
SMTP_PASS      = os.getenv("SMTP_PASS", "").strip()
SMTP_SSL       = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
SMTP_STARTTLS  = os.getenv("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes")

MAIL_FROM      = os.getenv("MAIL_FROM", SMTP_USER or "noreply@example.com").strip()
MAIL_BCC_RAW   = os.getenv("MAIL_BCC", "").strip()
MAIL_BCC       = [x.strip() for x in MAIL_BCC_RAW.split(",") if x.strip()]

log.info(
    "SMTP config -> server=%s port=%s ssl=%s starttls=%s user=%s from=%s",
    SMTP_SERVER, SMTP_PORT, SMTP_SSL, SMTP_STARTTLS, SMTP_USER, MAIL_FROM
)

# ------------------------------------------------------------------
# FastAPI
# ------------------------------------------------------------------
app = FastAPI(title="Astroservice", version="1.0")

# ------------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------------
def _resolve_host(host: str) -> str:
    """DNS-Check: gibt IP zurück oder wirft aussagekräftigen Fehler."""
    try:
        ip = socket.gethostbyname(host)
        log.info("DNS OK: %s -> %s", host, ip)
        return ip
    except socket.gaierror as e:
        msg = f"DNS-Fehler für '{host}': {e}"
        log.error(msg)
        raise RuntimeError(msg)

def _build_message(
    subject: str,
    to: EmailStr,
    html: str,
    text: Optional[str] = None,
    bcc: Optional[List[str]] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = str(to)
    if bcc:
        # BCC kommt nur im SMTP-Versand vor, nicht in den Header
        pass
    if text:
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
    else:
        # nur HTML
        msg.add_alternative(html, subtype="html")
    return msg

def _send_mail_sync(msg: EmailMessage, to: EmailStr, bcc: Optional[List[str]] = None) -> None:
    """Synchroner SMTP-Versand (von FastAPI als BackgroundTask aufgerufen)."""
    # 1) DNS testen – gibt im Fehlerfall klare Meldung zurück
    _resolve_host(SMTP_SERVER)

    recipients = [str(to)]
    if bcc:
        recipients += bcc

    log.info("Sende E-Mail an %s (BCC=%s) via %s:%s …",
             recipients, bool(bcc), SMTP_SERVER, SMTP_PORT)

    if SMTP_SSL:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=20) as smtp:
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg, from_addr=MAIL_FROM, to_addrs=recipients)
    else:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            if SMTP_STARTTLS:
                context = ssl.create_default_context()
                smtp.starttls(context=context)
                smtp.ehlo()
            if SMTP_USER and SMTP_PASS:
                smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg, from_addr=MAIL_FROM, to_addrs=recipients)

    log.info("E-Mail erfolgreich versendet.")

# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class Intake(BaseModel):
    mc_user_id: Optional[str] = None
    first_name: Optional[str] = None
    birth_date: Optional[str] = None  # TT.MM.JJJJ
    birth_time: Optional[str] = None  # HH:MM
    birth_place: Optional[str] = None
    email: EmailStr

# ------------------------------------------------------------------
# Endpunkte
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

@app.get("/mail/test")
def mail_test(
    background: BackgroundTasks,
    to: EmailStr = Query(..., description="Empfänger"),
):
    try:
        subject = "Astroservice – Test-E-Mail"
        html = """
        <h2>Hallo 👋</h2>
        <p>Das ist eine Test-Mail vom Astroservice.</p>
        <p>Wenn sie ankommt, ist deine SMTP-Konfiguration korrekt.</p>
        """
        text = "Test-Mail vom Astroservice. Wenn sie ankommt, ist SMTP ok."
        msg = _build_message(subject, to, html, text=text, bcc=MAIL_BCC)
        background.add_task(_send_mail_sync, msg, to, MAIL_BCC)
        return {"detail": "Test-Mail wird im Hintergrund versendet."}
    except Exception as e:
        log.exception("Mail-Test fehlgeschlagen")
        return JSONResponse(status_code=500, content={"detail": f"Mail-Fehler: {e}"})

@app.post("/mc/email-intake")
def mc_email_intake(background: BackgroundTasks, data: Intake):
    """Empfängt Daten aus ManyChat und verschickt eine Bestätigungs-Mail."""
    try:
        # Inhalt zusammenbauen
        subject = "Deine Traumort-Anfrage ist eingegangen ✨"
        html = f"""
        <h2>Danke{(' ' + data.first_name) if data.first_name else ''}! 🙏</h2>
        <p>Wir haben deine Angaben erhalten:</p>
        <ul>
          <li><b>Geburtsdatum:</b> {data.birth_date or '-'}</li>
          <li><b>Geburtszeit:</b> {data.birth_time or '-'}</li>
          <li><b>Geburtsort:</b> {data.birth_place or '-'}</li>
        </ul>
        <p>Du bekommst deine persönliche Traumort-Vorschau in Kürze per E-Mail.</p>
        <p>Herzliche Grüße<br/>Astroservice</p>
        """
        text = (
            "Danke! Wir haben deine Angaben erhalten.\n"
            f"Geburtsdatum: {data.birth_date or '-'}\n"
            f"Geburtszeit : {data.birth_time or '-'}\n"
            f"Geburtsort  : {data.birth_place or '-'}\n"
            "Du bekommst deine Traumort-Vorschau in Kürze per E-Mail."
        )

        msg = _build_message(subject, data.email, html, text=text, bcc=MAIL_BCC)
        background.add_task(_send_mail_sync, msg, data.email, MAIL_BCC)

        return {"detail": "Intake ok, Bestätigungs-Mail wird versendet."}
    except Exception as e:
        log.exception("Intake/Mail fehlgeschlagen")
        return JSONResponse(status_code=500, content={"detail": f"Mail-Fehler: {e}"})
