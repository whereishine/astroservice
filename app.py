from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import os, httpx, json

MANYCHAT_TOKEN = os.getenv("MANYCHAT_TOKEN", "DEIN_MANYCHAT_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "GEHEIMES_TOKEN")

app = FastAPI(title="Astroservice Webhook", docs_url="/docs", openapi_url="/openapi.json")

@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)

class Lead(BaseModel):
    mc_user_id: str = Field(..., description="ManyChat Subscriber ID (Instagram)")
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str

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

MANYCHAT_SEND_URL = "https://api.manychat.com/fb/sending/sendContent"
def _mc_headers():
    return {
        "Authorization": f"Bearer {MANYCHAT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "astroservice/1.0",
    }
def _mc_text_payload(subscriber_id: str, text: str) -> dict:
    return {
        "subscriber_id": subscriber_id,
        "data": {"version": "v2", "content": {"messages": [{"type": "text", "text": text}]}}
    }

async def send_dm(mc_user_id: str, text: str):
    if not MANYCHAT_TOKEN or MANYCHAT_TOKEN == "DEIN_MANYCHAT_API_KEY":
        return {"status": "error", "reason": "MANYCHAT_TOKEN missing or placeholder"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.post(MANYCHAT_SEND_URL, headers=_mc_headers(), json=_mc_text_payload(mc_user_id, text))
        body = resp.text[:1000]; ctype = resp.headers.get("content-type", "")
    try: return resp.json()
    except Exception: return {"non_json": True, "status_code": resp.status_code, "content_type": ctype, "body": body}

@app.post("/mc/webhook", summary="ManyChat Webhook (Instagram)")
async def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    if api_key != WEBHOOK_SECRET: raise HTTPException(status_code=401, detail="Unauthorized")
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)
    preview = build_preview_text(lead.first_name, results)
    mc_resp = await send_dm(lead.mc_user_id, preview)
    sent = isinstance(mc_resp, dict) and mc_resp.get("status") == "success"
    return {"status": "ok", "sent": sent, "preview": preview, "manychat": mc_resp}

@app.get("/mc/test", summary="Send test DM using /fb/sending/sendContent")
async def mc_test(subscriber_id: str):
    return await send_dm(subscriber_id, "Test aus /mc/test ✅")
