from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os

# ==========================================
# Security / Config
# ==========================================
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# FastAPI + Swagger
app = FastAPI(title="Astroservice Webhook (Preview only)", docs_url="/docs", openapi_url="/openapi.json")

# Authorize dialog expects this header name
api_key_header = APIKeyHeader(name="X-Auth-Token", auto_error=False)

# ==========================================
# Domain
# ==========================================
import generate_magic_places

class Lead(BaseModel):
    mc_user_id: str
    first_name: str
    birth_date: str
    birth_time: str
    birth_place: str

def run_astro_eval(birth_date: str, birth_time: str, birth_place: str):
    """Delegates to your existing astro logic and returns a dict with keys love/career/health (list[str])."""
    return generate_magic_places.get_magic_places(birth_date, birth_time, birth_place)

def build_preview_text(name: str, results: dict) -> str:
    love = ", ".join(results.get("love", [])[:3]) or "–"
    career = ", ".join(results.get("career", [])[:3]) or "–"
    health = ", ".join(results.get("health", [])[:3]) or "–"
    return (
        f"🎁 Danke {name}! Hier deine Traumorte 🌍✨\n\n"
        f"❤️ Liebe → {love}\n"
        f"🏆 Karriere → {career}\n"
        f"💚 Gesundheit → {health}\n\n"
        f"👉 Für deine ausführliche Analyse antworte: PREMIUM"
    )

# ==========================================
# Routes
# ==========================================
@app.get("/")
def root():
    return {"status": "ok", "service": "astroservice", "docs": "/docs"}

@app.post("/mc/webhook", summary="ManyChat Webhook (returns preview only)")
def mc_webhook(lead: Lead, api_key: str = Security(api_key_header)):
    # Simple header auth
    if api_key != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1) Evaluate
    results = run_astro_eval(lead.birth_date, lead.birth_time, lead.birth_place)

    # 2) Build preview text
    preview = build_preview_text(lead.first_name, results)

    # 3) Return to ManyChat for Response Mapping (no DM send here)
    return {
        "status": "ok",
        "sent": False,              # server sends nothing; ManyChat sends the DM
        "preview": preview,
        "love": results.get("love", []),
        "career": results.get("career", []),
        "health": results.get("health", []),
    }
