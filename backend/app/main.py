from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Fit360 AI API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(
    os.getenv(
        "FIT360_DB_PATH",
        str(Path(__file__).resolve().parents[1] / "fit360.db"),
    )
)
FASHN_BASE_URL = "https://api.fashn.ai/v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                height_cm REAL,
                preferred_style TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wardrobe_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                image_data TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS looks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                prediction_id TEXT,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                output_url TEXT,
                garment_name TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


init_db()


class StyleScoreRequest(BaseModel):
    blazer_color: str = "black and white"
    bottom_color: str = "white"
    top_color: str = "black"
    shoe_style: str = "slim retro sneakers"
    occasion: Literal["casual", "work", "dinner", "event", "travel"] = "casual"


class ProfileRequest(BaseModel):
    user_id: str = "demo"
    name: str = Field(default="My profile", min_length=1, max_length=80)
    height_cm: float | None = Field(default=None, ge=100, le=230)
    preferred_style: str = Field(default="modern tailored", max_length=120)


class WardrobeItemRequest(BaseModel):
    user_id: str = "demo"
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="other", max_length=40)
    image_data: str | None = None


class TryOnRequest(BaseModel):
    user_id: str = "demo"
    person_image: str = Field(min_length=1)
    garment_image: str = Field(min_length=1)
    category: str = "auto"
    garment_name: str | None = None


class LookRequest(BaseModel):
    user_id: str = "demo"
    prediction_id: str | None = None
    provider: str = "mock"
    status: str = "completed"
    output_url: str | None = None
    garment_name: str | None = None


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fit360-api", "version": "0.3.0"}


@app.get("/api/profile/{user_id}")
def get_profile(user_id: str) -> dict:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row_to_dict(row) or {
        "user_id": user_id,
        "name": "My profile",
        "height_cm": None,
        "preferred_style": "modern tailored",
        "updated_at": None,
    }


@app.post("/api/profile")
def save_profile(request: ProfileRequest) -> dict:
    updated_at = utc_now()
    with db() as connection:
        connection.execute(
            """
            INSERT INTO profiles (user_id, name, height_cm, preferred_style, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                height_cm = excluded.height_cm,
                preferred_style = excluded.preferred_style,
                updated_at = excluded.updated_at
            """,
            (
                request.user_id,
                request.name,
                request.height_cm,
                request.preferred_style,
                updated_at,
            ),
        )
    return {**request.model_dump(), "updated_at": updated_at}


@app.get("/api/wardrobe/{user_id}")
def list_wardrobe(user_id: str) -> dict:
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM wardrobe_items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/wardrobe")
def add_wardrobe_item(request: WardrobeItemRequest) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "name": request.name,
        "category": request.category,
        "image_data": request.image_data,
        "created_at": utc_now(),
    }
    with db() as connection:
        connection.execute(
            """
            INSERT INTO wardrobe_items (id, user_id, name, category, image_data, created_at)
            VALUES (:id, :user_id, :name, :category, :image_data, :created_at)
            """,
            item,
        )
    return item


@app.delete("/api/wardrobe/{item_id}")
def delete_wardrobe_item(item_id: str) -> dict[str, str]:
    with db() as connection:
        cursor = connection.execute(
            "DELETE FROM wardrobe_items WHERE id = ?",
            (item_id,),
        )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    return {"status": "deleted", "id": item_id}


@app.get("/api/looks/{user_id}")
def list_looks(user_id: str) -> dict:
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM looks WHERE user_id = ? ORDER BY created_at DESC LIMIT 24",
            (user_id,),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/looks")
def save_look(request: LookRequest) -> dict:
    look = {
        "id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "prediction_id": request.prediction_id,
        "provider": request.provider,
        "status": request.status,
        "output_url": request.output_url,
        "garment_name": request.garment_name,
        "created_at": utc_now(),
    }
    with db() as connection:
        connection.execute(
            """
            INSERT INTO looks (id, user_id, prediction_id, provider, status, output_url, garment_name, created_at)
            VALUES (:id, :user_id, :prediction_id, :provider, :status, :output_url, :garment_name, :created_at)
            """,
            look,
        )
    return look


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


def fashn_category(category: str) -> str:
    normalized = category.strip().lower()
    return {
        "top": "tops",
        "tops": "tops",
        "bottom": "bottoms",
        "bottoms": "bottoms",
        "dress": "one-pieces",
        "one-piece": "one-pieces",
        "one-pieces": "one-pieces",
    }.get(normalized, "auto")


@app.post("/api/tryon")
def try_on(request: TryOnRequest) -> dict:
    provider = os.getenv("FIT360_VTON_PROVIDER", "mock").strip().lower()

    if provider == "mock":
        prediction_id = f"mock-{uuid.uuid4()}"
        return {
            "status": "completed",
            "provider": "mock",
            "prediction_id": prediction_id,
            "output": [],
            "message": "Mock mode is active. Set FIT360_VTON_PROVIDER=fashn and FASHN_API_KEY to enable photorealistic try-on.",
        }

    if provider != "fashn":
        raise HTTPException(status_code=400, detail=f"Unsupported VTO provider: {provider}")

    api_key = os.getenv("FASHN_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="FASHN_API_KEY is not configured on the server.",
        )

    model_name = os.getenv("FIT360_VTON_MODEL", "tryon-v1.6").strip().lower()
    private_output = os.getenv("FIT360_PRIVATE_OUTPUT", "false").strip().lower() in {"1", "true", "yes"}

    if model_name == "tryon-max":
        inputs = {
            "model_image": request.person_image,
            "product_image": request.garment_image,
            "resolution": "1k",
            "generation_mode": "fast",
            "output_format": "jpeg",
            "return_base64": private_output,
        }
    else:
        model_name = "tryon-v1.6"
        inputs = {
            "model_image": request.person_image,
            "garment_image": request.garment_image,
            "category": fashn_category(request.category),
            "mode": "balanced",
            "output_format": "jpeg",
            "return_base64": private_output,
        }

    payload = {"model_name": model_name, "inputs": inputs}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{FASHN_BASE_URL}/run", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise HTTPException(status_code=502, detail=f"FASHN rejected the request: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"FASHN request failed: {exc}") from exc

    prediction_id = data.get("id")
    if not prediction_id:
        raise HTTPException(status_code=502, detail="FASHN did not return a prediction id.")

    return {
        "status": "queued",
        "provider": "fashn",
        "model": model_name,
        "prediction_id": prediction_id,
        "output": [],
    }


@app.get("/api/tryon/status/{prediction_id}")
def try_on_status(prediction_id: str) -> dict:
    if prediction_id.startswith("mock-"):
        return {
            "id": prediction_id,
            "status": "completed",
            "provider": "mock",
            "output": [],
            "error": None,
        }

    provider = os.getenv("FIT360_VTON_PROVIDER", "mock").strip().lower()
    api_key = os.getenv("FASHN_API_KEY")
    if provider != "fashn" or not api_key:
        raise HTTPException(status_code=503, detail="FASHN provider is not configured.")

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f"{FASHN_BASE_URL}/status/{prediction_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise HTTPException(status_code=502, detail=f"FASHN status request failed: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"FASHN status request failed: {exc}") from exc

    output = data.get("output") or []
    if isinstance(output, dict):
        output = output.get("images") or []

    return {
        "id": prediction_id,
        "status": data.get("status", "unknown"),
        "provider": "fashn",
        "output": output,
        "error": data.get("error"),
    }


from app.phase2 import router as phase2_router

app.include_router(phase2_router)
