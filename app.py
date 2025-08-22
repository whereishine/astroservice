from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os, httpx

# === Environment Variables ===
MANYCHAT_TOKEN = os.getenv("MANYCHAT_TOKEN", "DEIN_MANYCHAT_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "GEHEIMES_TOKEN")

# === FastAPI App (mit Docs) ===
app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

# === Security: API Key über Header (Swagger -> Authorize) ===
api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)

# === Eingangsmodell ===
class Lead(BaseModel):
    mc_user_id: str
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str

# === Deine Auswertungslogik ===
import generate_magic_places

def run_astro_eval(birth_date: str, birth_time: str, birth_place: str):
    return generate_magic_places.get_magic_places(birth_date, birth_time, birth_place)

def build_preview_text(name: str, results: dict) -> str:
    love = ", ".join(results.get("love", [])[:3])
    career = ", ".join(results.get("career", [])[:3])
    health = ", ".join(results.get("health", [])[:3])
    return (
        f"🎁 Danke {name}! Hier deine Traumorte 🌍✨\n\n"
        f"❤️ Liebe → {love}\n"
        f"🏆 Karriere → {career}\n"
        f"💚 Gesundheit → {health}\n\n"
        f"👉 Für deine ausführliche Analyse antworte: PREMIUM"
    )

async def send_dm(mc_user_id: str, text: str):
    if not MANYCHAT_TOKEN or MANYCHAT_TOKEN == "DEIN_MANYCHAT_API_KEY":
        # Token fehlt: Versand überspringen, aber nicht crashen
        return {"skipped": True, "reason": "MANYCHAT_TOKEN missing"}
    url = "https://api.manychat.com/fb/sending/sendMessage"
    headers = {"Authorization": f"Bearer {MANYCHAT_TOKEN}", "Content-Type": "application/json"}
    payload = {"subscriber_id": mc_user_id, "message": {"text": text}}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
    return r.json()

@app.post("/mc/webhook", summary="Mc Webhook")
async def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    # Auth prüfen (über Swagger -> Authorize oder über ManyChat-Header)
    if api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1) Auswertung
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2) Nachricht bauen
    preview = build_preview_text(lead.first_name, results)

    # 3) DM senden (soft-fail)
    sent = False
    try:
        resp = await send_dm(lead.mc_user_id, preview)
        # Wenn kein Fehler geworfen wurde, gilt als gesendet (auch wenn skipped)
        sent = isinstance(resp, dict) and not resp.get("skipped")
    except Exception:
        sent = False

    return {"status": "ok", "sent": sent, "preview": preview}
