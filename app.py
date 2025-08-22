from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import os, httpx, json

# ==============================
# Environment Variables
# ==============================
MANYCHAT_TOKEN = os.getenv("MANYCHAT_TOKEN", "DEIN_MANYCHAT_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "GEHEIMES_TOKEN")

# ==============================
# FastAPI app (with docs)
# ==============================
app = FastAPI(
    title="Astroservice Webhook",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

# Swagger → Authorize: erwartet Header X-Auth-Token
api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)

# ==============================
# Payload
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
    """Return dict with keys: love, career, health (list[str])."""
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

# ==============================
# ManyChat Instagram send
# ==============================
async def send_dm(mc_user_id: str, text: str):
    """Send an Instagram DM via ManyChat API. Always returns a dict (also on HTML/errors)."""
    if not MANYCHAT_TOKEN or MANYCHAT_TOKEN == "DEIN_MANYCHAT_API_KEY":
        return {"status": "error", "reason": "MANYCHAT_TOKEN missing or placeholder"}

    url = "https://api.manychat.com/instagram/sending/sendMessage"  # IG-Endpoint
    headers = {
        "Authorization": f"Bearer {MANYCHAT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "astroservice/1.0",
    }
    payload = {"subscriber_id": mc_user_id, "message": {"text": text}}

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.post(url, headers=headers, json=payload)
        text_body = resp.text[:800]  # trim for safety
        content_type = resp.headers.get("content-type", "")

    try:
        data = json.loads(text_body)
    except json.JSONDecodeError:
        data = {"status": "error", "non_json": True, "status_code": resp.status_code,
                "content_type": content_type, "body": text_body}
    return data

# ==============================
# Webhook
# ==============================
@app.post("/mc/webhook", summary="ManyChat Webhook (Instagram)")
async def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    # Auth
    if api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1) Auswertung
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2) Nachricht
    preview = build_preview_text(lead.first_name, results)

    # 3) DM senden
    mc_resp = await send_dm(lead.mc_user_id, preview)
    sent = isinstance(mc_resp, dict) and mc_resp.get("status") == "success"

    return {"status": "ok", "sent": sent, "preview": preview, "manychat": mc_resp}

# ==============================
# Debug helpers
# ==============================
@app.get("/mc/ping", summary="Check ManyChat token/account JSON")
async def mc_ping():
    if not MANYCHAT_TOKEN:
        raise HTTPException(status_code=500, detail="MANYCHAT_TOKEN missing")
    url = "https://api.manychat.com/account"
    headers = {"Authorization": f"Bearer {MANYCHAT_TOKEN}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
    text_body = resp.text[:800]
    try:
        data = resp.json()
    except Exception:
        data = {"non_json": True, "status_code": resp.status_code,
                "content_type": resp.headers.get("content-type", ""), "body": text_body}
    return data

@app.get("/mc/test", summary="Send a test DM to subscriber_id")
async def mc_test(subscriber_id: str):
    text = "Test aus /mc/test ✅"
    url = "https://api.manychat.com/instagram/sending/sendMessage"
    headers = {
        "Authorization": f"Bearer {MANYCHAT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "astroservice/1.0",
    }
    payload = {"subscriber_id": subscriber_id, "message": {"text": text}}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.post(url, headers=headers, json=payload)
    text_body = resp.text[:800]
    try:
        data = resp.json()
    except Exception:
        data = {"non_json": True, "status_code": resp.status_code, "body": text_body}
    return data
