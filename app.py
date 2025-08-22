from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import os, httpx

# ==============================
# Environment
# ==============================
MANYCHAT_TOKEN = os.getenv("MANYCHAT_TOKEN", "DEIN_MANYCHAT_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "GEHEIMES_TOKEN")

# ==============================
# FastAPI app (with docs)
# ==============================
app = FastAPI(
    title="Astroservice Webhook",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

# Security: API Key via header for Swagger "Authorize" dialog
api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)

# ==============================
# Payload model
# ==============================
class Lead(BaseModel):
    mc_user_id: str = Field(..., description="ManyChat Subscriber ID (Instagram)")
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str

# ==============================
# Domain logic
# ==============================
import generate_magic_places

def run_astro_eval(birth_date: str, birth_time: str, birth_place: str):
    """Return a dict with keys: love, career, health (list[str])."""
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
    """Send Instagram DM via ManyChat API. Returns ManyChat JSON or a 'skipped' dict."""
    if not MANYCHAT_TOKEN or MANYCHAT_TOKEN == "DEIN_MANYCHAT_API_KEY":
        # Token fehlt: Versand überspringen, aber nicht crashen
        return {"skipped": True, "reason": "MANYCHAT_TOKEN missing"}

    # ✅ Instagram endpoint (not the Facebook one)
    url = "https://api.manychat.com/instagram/sending/sendMessage"
    headers = {"Authorization": f"Bearer {MANYCHAT_TOKEN}", "Content-Type": "application/json"}
    payload = {"subscriber_id": mc_user_id, "message": {"text": text}}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        # don't crash on non-2xx; let caller inspect response
        try:
            data = r.json()
        except Exception:
            raw = await r.aread()
            data = {"parse_error": True, "raw": raw.decode(errors="ignore"), "status_code": r.status_code}

    return data

# ==============================
# Webhook
# ==============================
@app.post("/mc/webhook", summary="ManyChat Webhook (Instagram)")
async def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    # Auth check
    if api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1) Auswertung
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2) Nachricht bauen
    preview = build_preview_text(lead.first_name, results)

    # 3) DM senden
    sent = False
    mc_resp = None
    try:
        mc_resp = await send_dm(lead.mc_user_id, preview)
        # Erfolg nur wenn ManyChat "success" meldet
        if isinstance(mc_resp, dict) and mc_resp.get("status") == "success":
            sent = True
    except Exception as e:
        mc_resp = {"error": str(e)}

    return {"status": "ok", "sent": sent, "preview": preview, "manychat": mc_resp}
