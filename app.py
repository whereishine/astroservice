# app.py  (FastAPI)
from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
import os
import smtplib, ssl
from email.mime.text import MIMEText

app = FastAPI(title="Astroservice", version="1.0")

class Intake(BaseModel):
    mc_user_id: str | None = None
    first_name: str
    email: EmailStr | None = None
    birth_date: str
    birth_time: str
    birth_place: str

def build_preview(d: Intake) -> str:
    # Hier nur eine einfache Vorschau – später ersetzen wir das
    lines = [
        f"Hi {d.first_name},",
        "",
        "Deine Traumort-Vorschau:",
        f"• Geburtsdatum: {d.birth_date}",
        f"• Geburtszeit:  {d.birth_time}",
        f"• Geburtsort:   {d.birth_place}",
        "",
        "Für die ausführliche Analyse: PREMIUM.",
    ]
    return "\n".join(lines)

def try_send_email(to_addr: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    pw   = os.getenv("SMTP_PASS")
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("MAIL_FROM", "Shine <no-reply@whereishine.com>")

    if not (host and user and pw and to_addr):
        return False

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, pw)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    return True

@app.get("/health")
def health():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

@app.post("/mc/email-intake")
def email_intake(data: Intake):
    preview = build_preview(data)
    sent = False
    if data.email:
        sent = try_send_email(
            data.email,
            "Deine Traumort‑Vorschau",
            preview
        )
    return {"status": "ok", "sent_email": sent, "preview": preview}

# optionaler GET-Test (z.B. im Browser)
@app.get("/mail/test")
def mail_test(to: EmailStr):
    body = "Testmail von Astroservice."
    sent = try_send_email(str(to), "Astroservice Test", body)
    return {"status": "ok" if sent else "skip", "to": to}
