import os
from flask import Flask, request, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

APP_NAME = "astroservice"
app = Flask(APP_NAME)

# Helper: build HTML preview block from list/strings
def build_preview_html(preview):
    if isinstance(preview, list):
        items = "".join(f"<li>{x}</li>" for x in preview)
        return f"<ul>{items}</ul>"
    if isinstance(preview, dict):
        items = "".join(f"<li><b>{k}</b>: {v}</li>" for k, v in preview.items())
        return f"<ul>{items}</ul>"
    return f"<p>{preview}</p>"

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": APP_NAME})

@app.post("/email/send")
def email_send():
    data = request.get_json(silent=True) or {}
    # required fields
    to_email = data.get("to_email")
    first_name = data.get("first_name", "")
    preview = data.get("preview")

    if not to_email or preview is None:
        return jsonify({"detail": "Missing required fields: to_email, preview"}), 422

    # SMTP config from environment
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL") or smtp_user

    if not all([smtp_host, smtp_user, smtp_pass, from_email]):
        return jsonify({"detail": "SMTP environment not fully configured"}), 500

    subject = "Deine persönlichen Traumorte – Kurzvorschau"
    # Build body
    preview_html = build_preview_html(preview)
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>Hallo {first_name or ''} 👋</h2>
        <p>Hier ist deine kostenlose Kurzvorschau deiner <b>Traumorte</b> anhand deiner Angaben.</p>
        {preview_html}
        <hr />
        <p>Wenn du möchtest, erstelle ich dir gern eine <b>Premium-Auswertung</b> mit Karte,
        konkreten Handlungstipps & Prioritäten – antworte einfach auf diese E-Mail.</p>
        <p>Liebe Grüße,<br/>Astroservice</p>
      </body>
    </html>
    """
    text_body = f"""Hallo {first_name or ''}

Hier ist deine Kurzvorschau deiner Traumorte:

{preview if isinstance(preview, str) else str(preview)}

Für eine Premium-Auswertung (inkl. Karte und Empfehlungen) antworte einfach auf diese E-Mail.

Liebe Grüße
Astroservice
"""

    # Compose email
    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Send via SMTP (STARTTLS)
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
    except Exception as e:
        return jsonify({"detail": "SMTP send failed", "error": str(e)}), 500

    return jsonify({"status": "sent", "to": to_email})
    
if __name__ == "__main__":
    # For local debug only; on Railway a WSGI server will be used by default
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
