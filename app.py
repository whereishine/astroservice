# app.py
from __future__ import annotations

import os
import smtplib
import ssl
import socket
import logging
from email.message import EmailMessage
from typing import Optional, List

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("astroservice")

# SMTP Debug (0/1/2), gibt SMTP-Konversation in den Deploy-Logs aus
SMTP_DEBUG = int(os.getenv("MAIL_DEBUG", "0"))

# -----------------------------------------------------------------------------
# Konfiguration (aus Umgebungsvariablen)
# -----------------------------------------------------------------------------
SMTP_SERVER   = os.getenv("SMTP_SERVER", "w00edb59.kasserver.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))       # 465 (SSL) oder 587 (STARTTLS)
SMTP_SSL      = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes")
SMTP_USER     = os.getenv("SMTP_USER")                   # z.B. info@whereishine.com
SMTP_PASS     = os.getenv("SMTP_PASS")
MAIL_FROM     = os.getenv("MAIL_FROM", SMTP_USER or "noreply@example.com")
MAIL_BCC      = os.getenv("MAIL_BCC", "")               # kommaseparierte Liste

if not SMTP_USER or not SMTP_PASS:
    log.warning("SMTP_USER/SMTP_PASS fehlen (E-Mails können fehlschlagen).")

log.info(
    "SMTP config -> server=%s port=%s ssl=%s starttls=%s user=%s from=%s",
    SMTP_SERVER, SMTP_PORT, SMTP_SSL, SMTP_STARTTLS, SMTP_USER, MAIL_FROM
)

# -----------------------------------------------------------------------------
# Hilfen
# -----------------------------------------------------------------------------
def _resolve_host(host: str) -> Optional[str]:
    try:
        ip = socket.gethostbyname(host)
        return ip
    except Exception as e:
        log.error("DNS-Auflösung fehlgeschlagen: %s -> %s", host, e)
        return None

def _parse_bcc(raw: str) -> List[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]

def _open_smtp() -> smtplib.SMTP:
    """
    Baut die SMTP-Verbindung auf (SSL oder STARTTLS).
    Wirft Exception bei Fehlern.
    """
    timeout = 30
    context = ssl.create_default_context()

    if SMTP_SSL:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=timeout)
        if SMTP_DEBUG:
            server.set_debuglevel(1)
        # vielen Hostern ist ein "EHLO" + STARTTLS wichtig
        server.ehlo()
        if SMTP_STARTTLS:
            server.starttls(context=context)
            server.ehlo()

    if SMTP_DEBUG and SMTP_SSL:
        # Bei SSL Verbindung kann Debuglevel trotzdem gesetzt werden
        server.set_debuglevel(1)

    if SMTP_USER and SMTP_PASS:
        server.login(SMTP_USER, SMTP_PASS)
    return server

def send_email(to: EmailStr, subject: str, html: str, text: Optional[str] = None, reply_to: Optional[str] = None) -> dict:
    """
    Versendet direkt (synchron) eine E-Mail und gibt ein Ergebnis-Dict zurück.
    Wirft HTTPException bei harten Fehlern.
    """
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = str(to)
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    if text:
        msg.set_content(text)

    # HTML als Alternative
    msg.add_alternative(html, subtype="html")

    # BCC hinzufügen (ohne Header)
    bcc_list = _parse_bcc(MAIL_BCC)
    all_rcpts = [str(to)] + bcc_list

    try:
        server = _open_smtp()
        # send_message nutzt Empfänger aus Headern; wir geben die Liste explizit an
        server.send_message(msg, from_addr=MAIL_FROM, to_addrs=all_rcpts)
        try:
            server.quit()
        except Exception:
            server.close()
        log.info("Mail erfolgreich versendet -> to=%s bcc=%s", to, bcc_list)
        return {"status": "ok", "to": str(to), "bcc": bcc_list}
    except smtplib.SMTPAuthenticationError as e:
        log.error("SMTP Auth-Fehler: %s", e)
        raise HTTPException(status_code=400, detail="SMTP-Authentifizierung fehlgeschlagen (Benutzer/Passwort prüfen).")
    except smtplib.SMTPConnectError as e:
        log.error("SMTP Connect-Fehler: %s", e)
        raise HTTPException(status_code=502, detail="SMTP-Verbindung fehlgeschlagen (Server/Port/Firewall prüfen).")
    except smtplib.SMTPException as e:
        log.error("SMTP Fehler: %s", e)
        raise HTTPException(status_code=502, detail=f"SMTP-Fehler: {e}")
    except Exception as e:
        log.error("Allgemeiner Mail-Fehler: %s", e)
        raise HTTPException(status_code=500, detail=f"Mail-Fehler: {e}")

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Astroservice",
    version="1.0",
    description="E-Mail Versand + ManyChat Intake",
)

# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
class Intake(BaseModel):
    mc_user_id: Optional[str] = Field(None, description="ManyChat Contact ID")
    first_name: Optional[str] = None
    email: EmailStr
    birth_date: Optional[str] = Field(None, description="TT.MM.JJJJ")
    birth_time: Optional[str] = Field(None, description="z. B. 14:35")
    birth_place: Optional[str] = None

# -----------------------------------------------------------------------------
# Endpunkte
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    resolved = _resolve_host(SMTP_SERVER)
    return {
        "status": "ok",
        "service": "astroservice",
        "docs": "/docs",
        "smtp": {
            "server": SMTP_SERVER,
            "resolved_ip": resolved,
            "port": SMTP_PORT,
            "ssl": SMTP_SSL,
            "starttls": SMTP_STARTTLS,
            "user_set": bool(SMTP_USER),
            "from": MAIL_FROM,
            "bcc": _parse_bcc(MAIL_BCC),
            "debug": SMTP_DEBUG,
        },
    }

@app.get("/mail/test")
def mail_test(
    to: EmailStr = Query(..., description="Empfänger-Adresse für den Test"),
    subject: str = Query("Astroservice – Test", description="Betreff"),
    body: str = Query("Das ist eine Testmail vom Astroservice.", description="Klartext für die Mail"),
):
    html = f"<p>{body}</p><p><small>Gesendet von Astroservice.</small></p>"
    result = send_email(to=to, subject=subject, html=html, text=body)
    return result

@app.post("/mc/email-intake")
def mc_email_intake(data: Intake):
    """
    Nimmt die ManyChat-Daten entgegen und sendet eine Auswertung per E-Mail.
    (Die "Traumorte"-Logik ist hier nur exemplarisch skizziert.)
    """
    if not data.email:
        raise HTTPException(status_code=422, detail="E-Mail-Adresse fehlt.")

    # -> hier würde Deine eigentliche Auswertungslogik laufen
    traumorte = [
        "🌍 Bali – Kreativität & Leichtigkeit",
        "🏔️ Schweiz – Struktur & Fokus",
        "🌊 Lissabon – Flow & Inspiration",
    ]

    subject = "Deine Traumort-Auswertung"
    text = (
        f"Hallo {data.first_name or ''}\n\n"
        "Hier sind drei mögliche Traumorte für Dich:\n"
        + "\n".join(f"- {t}" for t in traumorte)
        + "\n\nDu bekommst weitere Details bald per E-Mail.\n"
    )
    html_lines = "".join(f"<li>{t}</li>" for t in traumorte)
    html = f"""
    <h3>Hallo {data.first_name or ''}</h3>
    <p>Hier sind drei mögliche Traumorte für Dich:</p>
    <ul>{html_lines}</ul>
    <p><small>Automatisch erstellt – Astroservice</small></p>
    """

    result = send_email(to=data.email, subject=subject, html=html, text=text)
    return {"status": "ok", "sent": result}

# Root (optional)
@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}
