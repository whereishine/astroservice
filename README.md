# Astro Service – Instagram DM Webhook (FastAPI)

Dieser kleine Service nimmt Daten aus ManyChat (Instagram DM) entgegen, führt deine Astrokartografie-Logik aus
und sendet automatisch eine DM mit einer Mini‑Auswertung zurück.

## 1) Dateien
- `app.py` – FastAPI Webhook + ManyChat DM Versand
- `generate_magic_places.py` – Platzhalterfunktion `get_magic_places(...)` (später durch echte Logik ersetzen)
- `requirements.txt` – Python Abhängigkeiten
- `Procfile` – Startbefehl für Railway/Heroku
- `.gitignore` – ignoriert venv, Cache, etc.

## 2) Lokal testen
```bash
pip install -r requirements.txt
export MANYCHAT_TOKEN="DEIN_MANYCHAT_API_KEY"
export WEBHOOK_SECRET="DEIN_GEHEIMES_TOKEN"
uvicorn app:app --reload --port 8000
```

Danach erreichbar:
- Webhook: `POST http://localhost:8000/mc/webhook`
- API Docs (automatisch): `http://localhost:8000/docs`

## 3) GitHub Repo erstellen
1. Gehe auf https://github.com → **New repository** → Name z. B. `astro_service` → **Create repository**.
2. Klicke **Upload files** → Ziehe alle Dateien aus diesem Ordner hier rein → **Commit changes**.

## 4) Railway Deployment (CI/CD)
1. https://railway.app → Sign up mit GitHub → Zugriff erlauben.
2. **New Project** → **Deploy from GitHub repo** → wähle dein `astro_service` Repo.
3. Warte bis der Build durch ist. Railway erkennt `requirements.txt` + `Procfile` automatisch.
4. **Environment Variables** setzen (Project → Variables):
   - `MANYCHAT_TOKEN` → ManyChat API Token (Settings → API)
   - `WEBHOOK_SECRET` → geheimes Token (auch in ManyChat als Header verwenden)
5. Nach dem Deploy findest du die **Public URL**, z. B. `https://astro-service.up.railway.app`.

## 5) ManyChat External Request (Flow Schritt)
- URL: `https://<deine-domain>.up.railway.app/mc/webhook`
- Headers:
  - `Content-Type: application/json`
  - `X-Auth-Token: <WEBHOOK_SECRET>`
- Body (RAW JSON):
```json
{
  "mc_user_id": "{{user.id}}",
  "first_name": "{{user.first_name}}",
  "birth_date": "{{user.birth_date}}",
  "birth_time": "{{user.birth_time}}",
  "birth_place": "{{user.birth_place}}"
}
```

## 6) Test
- In Instagram Kommentar „MEIN TRAUMORT“ → ManyChat sammelt Daten → schickt an Webhook.
- DM kommt automatisch mit Mini‑Auswertung.

## 7) Automatisches Update (CI/CD)
Sobald du Änderungen in GitHub **pushst** (oder per Web‑UI neue Commits erstellst), triggert Railway automatisch
ein neues **Deploy**. Stelle sicher, dass **Auto‑Deploy** im Railway Service **aktiviert** ist.

## 8) Fehlerbehebung
- **401 Unauthorized** → `X-Auth-Token` im ManyChat Header stimmt nicht mit `WEBHOOK_SECRET` überein.
- **403/400 von ManyChat API** beim Senden → falscher/abgelaufener Token `MANYCHAT_TOKEN` oder `subscriber_id` ungültig.
- **App startet nicht** → Prüfe Railway Logs; Port muss `$PORT` sein (über `Procfile` korrekt gesetzt).
- **CORS/Timeout** → ManyChat Timeout ~10s einhalten; Logik schlank halten, ggf. spätere E-Mail/PDF asynchron.

Viel Erfolg! 🚀
