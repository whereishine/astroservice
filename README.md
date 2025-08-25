# Astro Email Service (Railway)

Kleiner Flask-Dienst, der eine Vorschau der Traumorte per E‑Mail versendet.

## Endpunkte

- `GET /health` – Status
- `POST /email/send` – E-Mail senden

### Beispiel-Request (curl)

```
curl -X POST https://WEB-URL/email/send \
  -H "Content-Type: application/json" \
  -d '{
        "to_email": "kunde@example.com",
        "first_name": "Hannes",
        "preview": ["Venus-Linie – Partnerschaft & Schönheit", "Sonne-MC – Strahlkraft & Berufung"]
      }'
```

## Benötigte Environment-Variablen (Railway → Variables)

- `SMTP_HOST` – z. B. `smtp.gmail.com` oder `smtp.strato.de`
- `SMTP_PORT` – meist `587` (STARTTLS)
- `SMTP_USER` – SMTP-Login (komplette E‑Mail-Adresse)
- `SMTP_PASS` – SMTP-Passwort / App-Passwort
- `FROM_EMAIL` – Absender (optional, Standard = `SMTP_USER`)

## Start lokal

```
pip install -r requirements.txt
export SMTP_HOST=...
export SMTP_PORT=587
export SMTP_USER=...
export SMTP_PASS=...
python app.py
```
