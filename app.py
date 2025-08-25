from flask import Flask, request, jsonify
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

app = Flask(__name__)

# --- kleine Health- und Info-Endpoints ---
@app.get("/status")
def status():
    return jsonify({"status": "ok", "service": "astroservice", "docs": "/docs"})

@app.get("/docs")
def docs():
    return jsonify({
        "POST /email/send": {
            "headers": {"Content-Type": "application/json", "X-Auth-Token": "<SEND_KEY> (optional, s.u.)"},
            "body": {
                "first_name": "Max",
                "email": "kunde@example.com",
                "birth_date": "TT.MM.JJJJ",
                "birth_time": "HH:MM",
                "birth_place": "Ort"
            }
        }
    })

# --- Mail-Helfer ---
def send_mail(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM", user or "no-reply@example.com")
    from_name  = os.getenv("SMTP_FROM_NAME", "Astroservice")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and pwd:
            server.login(user, pwd)
        server.send_message(msg)

# --- Endpoint: E-Mail senden ---
@app.post("/email/send")
def email_send():
    # optionales Token (X-Auth-Token) prüfen, falls gesetzt
    required_token = os.getenv("SEND_KEY")
    got_token = request.headers.get("X-Auth-Token")
    if required_token:
        if not got_token or got_token != required_token:
            return jsonify({"detail": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name", "").strip()
    email      = data.get("email", "").strip()
    bdate      = data.get("birth_date", "").strip()
    btime      = data.get("birth_time", "").strip()
    bplace     = data.get("birth_place", "").strip()

    if not email:
        return jsonify({"detail": "Email is required"}), 422

    # einfacher Preview-Text (Platzhalter)
    preview = (
        f"Hey {first_name or 'du'},\n\n"
        f"deine Traumort‑Daten sind angekommen:\n"
        f"• Geburtsdatum: {bdate}\n"
        f"• Geburtszeit:  {btime}\n"
        f"• Geburtsort:   {bplace}\n\n"
        "Deine persönliche Auswertung folgt in Kürze. 🙌"
    )

    try:
        send_mail(
            to_email=email,
            subject="Deine Traumort‑Auswertung (Eingangsbestätigung)",
            body=preview
        )
    except Exception as e:
        return jsonify({"detail": "Mail send failed", "error": str(e)}), 500

    return jsonify({"status": "ok", "preview": preview})
    
if __name__ == "__main__":
    # lokaler Start (Railway nutzt gunicorn s. Procfile)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
