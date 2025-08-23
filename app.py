# app.py
# Astroservice Webhook (Preview-only sending handled by ManyChat)
# ---------------------------------------------------------------
# This service receives lead data from ManyChat, calculates the
# "Magic Places" preview text, and RETURNS the text in JSON.
# IMPORTANT: The service does NOT send any DMs itself. ManyChat
# should send the message in your Flow using the returned value.

import os
from fastapi import FastAPI, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# ---- Config
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # set in Render -> Environment

# ---- FastAPI app
app = FastAPI(title="Astroservice Webhook", version="0.1.0")

# Expect the secret from ManyChat in header: X-Auth-Token
api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)


# ---- Data models
class Lead(BaseModel):
    mc_user_id: str
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str


# ---- Your evaluation logic
# Make sure generate_magic_places.py is in the same repo
import generate_magic_places


def run_astro_eval(birth_date: str, birth_time: str, birth_place: str):
    """Wrapper around your evaluation logic."""
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


# ---- Endpoints
@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}


@app.post("/mc/webhook", summary="ManyChat Webhook (Instagram)")
async def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    """Receives lead data from ManyChat and returns preview text and top3 lists.
    This endpoint does NOT send messages. Send them from ManyChat Flow.
    """
    if not api_key or api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1) Calculate results
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2) Build preview text
    preview = build_preview_text(lead.first_name, results)

    # 3) Return data for ManyChat to send
    return {
        "status": "ok",
        "preview": preview,
        "love_top3": results.get("love", [])[:3],
        "career_top3": results.get("career", [])[:3],
        "health_top3": results.get("health", [])[:3],
    }


@app.get("/mc/test", summary="Test endpoint (no sending here)")
def mc_test(subscriber_id: str = Query(..., description="ManyChat subscriber id"),
            text: str = Query("Test", description="Preview text placeholder"),
            tag: str | None = Query(None, description="Optional message tag placeholder")):
    """This endpoint is only for quick checks.
    It never sends DMs; sending is done by ManyChat in the Flow."""
    return {
        "status": "ok",
        "note": "Test-Endpoint – Nachrichten werden von ManyChat gesendet, nicht hier.",
        "subscriber_id": subscriber_id,
        "text": text,
        "tag": tag
    }


# If you run locally:
# uvicorn app:app --host 0.0.0.0 --port 10000
