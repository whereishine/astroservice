from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os, httpx

# ENV Variablen (setzen auf Server, z.B. Railway/Render)
MANYCHAT_TOKEN = os.getenv("MANYCHAT_TOKEN", "DEIN_MANYCHAT_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "GEHEIMES_TOKEN")

app = FastAPI()

# Eingehende Datenstruktur
class Lead(BaseModel):
    mc_user_id: str
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str

# --- Deine Auswertungslogik importieren ---
import generate_magic_places

def run_astro_eval(birth_date, birth_time, birth_place):
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
    url = "https://api.manychat.com/fb/sending/sendMessage"
    headers = {"Authorization": f"Bearer {MANYCHAT_TOKEN}", "Content-Type": "application/json"}
    payload = {"subscriber_id": mc_user_id, "message": {"text": text}}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
    return r.json()

@app.post("/mc/webhook")
async def mc_webhook(request: Request, lead: Lead):
    # Auth check
    if request.headers.get("X-Auth-Token") != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1. Auswertung
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2. Nachricht bauen
    preview = build_preview_text(lead.first_name, results)

    # 3. DM senden
    await send_dm(lead.mc_user_id, preview)

    return {"status": "ok", "sent": True, "preview": preview}
