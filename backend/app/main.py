from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Fit360 AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StyleScoreRequest(BaseModel):
    blazer_color: str = "black and white"
    bottom_color: str = "white"
    top_color: str = "black"
    shoe_style: str = "slim retro sneakers"
    occasion: Literal["casual", "work", "dinner", "event", "travel"] = "casual"


class TryOnRequest(BaseModel):
    person_image_url: str = Field(min_length=1)
    garment_image_url: str = Field(min_length=1)
    category: str = "top"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fit360-api"}


@app.get("/api/trends")
def trends() -> dict:
    return {
        "season": "fall",
        "items": [
            {"name": "slim retro sneakers", "score": 94, "why": "clean profile works with tailoring"},
            {"name": "burgundy bag", "score": 91, "why": "adds a strong fall accent"},
            {"name": "fitted black top", "score": 89, "why": "balances a patterned blazer"},
            {"name": "pointed ankle boots", "score": 87, "why": "dressier alternative for evenings"},
        ],
    }


@app.post("/api/style/score")
def style_score(request: StyleScoreRequest) -> dict:
    score = 78
    notes: list[str] = []

    if request.blazer_color.lower() in {"black", "black and white", "black & white"}:
        score += 5
        notes.append("The blazer gives the outfit a strong tailored anchor.")
    if request.bottom_color.lower() in {"white", "cream", "ecru"}:
        score += 5
        notes.append("Light jeans keep the outfit sharp and modern.")
    if request.top_color.lower() in {"black", "white", "cream", "burgundy"}:
        score += 4
        notes.append("The top color works with the black-and-white palette.")
    if "retro" in request.shoe_style.lower() or "loafer" in request.shoe_style.lower():
        score += 4
        notes.append("Low-profile footwear keeps the proportions clean.")

    score = min(score, 98)
    return {
        "score": score,
        "label": "strong match" if score >= 88 else "good match",
        "notes": notes,
        "recommended_additions": ["burgundy bag", "gold earrings", "black belt"],
    }


@app.post("/api/tryon")
def try_on(request: TryOnRequest) -> dict:
    provider = os.getenv("FIT360_VTON_PROVIDER", "mock")
    return {
        "status": "queued" if provider != "mock" else "mock",
        "provider": provider,
        "person_image_url": request.person_image_url,
        "garment_image_url": request.garment_image_url,
        "category": request.category,
        "message": (
            "Virtual try-on provider hook is ready. Set FIT360_VTON_PROVIDER and add provider credentials to connect a commercial VTO API."
        ),
    }
