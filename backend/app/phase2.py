from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["fit360-phase2"])

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


def init_phase2_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS body_profiles (
                user_id TEXT PRIMARY KEY,
                bust_cm REAL,
                waist_cm REAL,
                hip_cm REAL,
                inseam_cm REAL,
                shoulder_cm REAL,
                shoe_eu REAL,
                fit_preference TEXT NOT NULL DEFAULT 'regular',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS catalog_products (
                id TEXT PRIMARY KEY,
                retailer_id TEXT NOT NULL,
                retailer_name TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                color TEXT NOT NULL,
                price_eur REAL NOT NULL,
                image_url TEXT,
                product_url TEXT,
                sizes_json TEXT NOT NULL,
                size_chart_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS multiview_sets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_image TEXT NOT NULL,
                garment_name TEXT,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                jobs_json TEXT NOT NULL,
                outputs_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        count = connection.execute("SELECT COUNT(*) AS n FROM catalog_products").fetchone()["n"]
        if count == 0:
            now = utc_now()
            products = [
                {
                    "id": "demo-blazer-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Tailored black blazer",
                    "category": "blazer",
                    "color": "black",
                    "price_eur": 89.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["XS", "S", "M", "L", "XL"]),
                    "size_chart_json": json.dumps(
                        {
                            "XS": {"bust": 82, "waist": 64, "hip": 90},
                            "S": {"bust": 86, "waist": 68, "hip": 94},
                            "M": {"bust": 92, "waist": 74, "hip": 100},
                            "L": {"bust": 98, "waist": 80, "hip": 106},
                            "XL": {"bust": 104, "waist": 86, "hip": 112},
                        }
                    ),
                    "tags_json": json.dumps(["tailored", "work", "dinner", "minimal"]),
                    "created_at": now,
                },
                {
                    "id": "demo-jeans-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Straight white jeans",
                    "category": "bottoms",
                    "color": "white",
                    "price_eur": 49.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["34", "36", "38", "40", "42", "44"]),
                    "size_chart_json": json.dumps(
                        {
                            "34": {"waist": 64, "hip": 90, "inseam": 78},
                            "36": {"waist": 68, "hip": 94, "inseam": 78},
                            "38": {"waist": 72, "hip": 98, "inseam": 79},
                            "40": {"waist": 76, "hip": 102, "inseam": 79},
                            "42": {"waist": 80, "hip": 106, "inseam": 80},
                            "44": {"waist": 84, "hip": 110, "inseam": 80},
                        }
                    ),
                    "tags_json": json.dumps(["clean", "casual", "work", "straight"]),
                    "created_at": now,
                },
                {
                    "id": "demo-top-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Fitted black bodysuit",
                    "category": "top",
                    "color": "black",
                    "price_eur": 29.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["XS", "S", "M", "L", "XL"]),
                    "size_chart_json": json.dumps(
                        {
                            "XS": {"bust": 80, "waist": 62},
                            "S": {"bust": 84, "waist": 66},
                            "M": {"bust": 90, "waist": 72},
                            "L": {"bust": 96, "waist": 78},
                            "XL": {"bust": 102, "waist": 84},
                        }
                    ),
                    "tags_json": json.dumps(["fitted", "minimal", "dinner", "work"]),
                    "created_at": now,
                },
                {
                    "id": "demo-bag-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Burgundy structured bag",
                    "category": "bag",
                    "color": "burgundy",
                    "price_eur": 59.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["ONE SIZE"]),
                    "size_chart_json": json.dumps({}),
                    "tags_json": json.dumps(["fall", "dinner", "work", "accent"]),
                    "created_at": now,
                },
                {
                    "id": "demo-shoes-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Slim retro sneakers",
                    "category": "shoes",
                    "color": "black and white",
                    "price_eur": 69.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["36", "37", "38", "39", "40", "41"]),
                    "size_chart_json": json.dumps(
                        {
                            "36": {"shoe_eu": 36},
                            "37": {"shoe_eu": 37},
                            "38": {"shoe_eu": 38},
                            "39": {"shoe_eu": 39},
                            "40": {"shoe_eu": 40},
                            "41": {"shoe_eu": 41},
                        }
                    ),
                    "tags_json": json.dumps(["retro", "casual", "travel", "low-profile"]),
                    "created_at": now,
                },
                {
                    "id": "demo-boots-001",
                    "retailer_id": "demo-store",
                    "retailer_name": "Demo Fashion Store",
                    "name": "Pointed ankle boots",
                    "category": "shoes",
                    "color": "black",
                    "price_eur": 99.0,
                    "image_url": None,
                    "product_url": None,
                    "sizes_json": json.dumps(["36", "37", "38", "39", "40", "41"]),
                    "size_chart_json": json.dumps(
                        {
                            "36": {"shoe_eu": 36},
                            "37": {"shoe_eu": 37},
                            "38": {"shoe_eu": 38},
                            "39": {"shoe_eu": 39},
                            "40": {"shoe_eu": 40},
                            "41": {"shoe_eu": 41},
                        }
                    ),
                    "tags_json": json.dumps(["dinner", "event", "tailored", "fall"]),
                    "created_at": now,
                },
            ]
            connection.executemany(
                """
                INSERT INTO catalog_products (
                    id, retailer_id, retailer_name, name, category, color, price_eur,
                    image_url, product_url, sizes_json, size_chart_json, tags_json, created_at
                ) VALUES (
                    :id, :retailer_id, :retailer_name, :name, :category, :color, :price_eur,
                    :image_url, :product_url, :sizes_json, :size_chart_json, :tags_json, :created_at
                )
                """,
                products,
            )


init_phase2_db()


class BodyProfileRequest(BaseModel):
    user_id: str = "demo"
    bust_cm: float | None = Field(default=None, ge=50, le=180)
    waist_cm: float | None = Field(default=None, ge=45, le=180)
    hip_cm: float | None = Field(default=None, ge=50, le=200)
    inseam_cm: float | None = Field(default=None, ge=45, le=120)
    shoulder_cm: float | None = Field(default=None, ge=25, le=70)
    shoe_eu: float | None = Field(default=None, ge=30, le=52)
    fit_preference: Literal["slim", "regular", "relaxed"] = "regular"


class CatalogProductRequest(BaseModel):
    retailer_id: str = Field(min_length=1, max_length=100)
    retailer_name: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=60)
    color: str = Field(default="unknown", max_length=80)
    price_eur: float = Field(ge=0)
    image_url: str | None = None
    product_url: str | None = None
    sizes: list[str] = []
    size_chart: dict[str, dict[str, float]] = {}
    tags: list[str] = []


class FitRecommendRequest(BaseModel):
    user_id: str = "demo"
    product_id: str


class CompleteLookRequest(BaseModel):
    user_id: str = "demo"
    anchor_product_id: str | None = None
    occasion: Literal["casual", "work", "dinner", "event", "travel"] = "casual"
    max_budget_eur: float | None = Field(default=None, ge=0)


class MultiViewRequest(BaseModel):
    user_id: str = "demo"
    source_image: str = Field(min_length=1)
    garment_name: str | None = None


def decode_product(row: sqlite3.Row) -> dict:
    product = dict(row)
    product["sizes"] = json.loads(product.pop("sizes_json"))
    product["size_chart"] = json.loads(product.pop("size_chart_json"))
    product["tags"] = json.loads(product.pop("tags_json"))
    return product


def get_product(product_id: str) -> dict:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM catalog_products WHERE id = ?",
            (product_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Catalog product not found")
    return decode_product(row)


def get_body_profile(user_id: str) -> dict:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM body_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else {
        "user_id": user_id,
        "bust_cm": None,
        "waist_cm": None,
        "hip_cm": None,
        "inseam_cm": None,
        "shoulder_cm": None,
        "shoe_eu": None,
        "fit_preference": "regular",
        "updated_at": None,
    }


@router.get("/body-profile/{user_id}")
def body_profile(user_id: str) -> dict:
    return get_body_profile(user_id)


@router.post("/body-profile")
def save_body_profile(request: BodyProfileRequest) -> dict:
    payload = {**request.model_dump(), "updated_at": utc_now()}
    with db() as connection:
        connection.execute(
            """
            INSERT INTO body_profiles (
                user_id, bust_cm, waist_cm, hip_cm, inseam_cm, shoulder_cm,
                shoe_eu, fit_preference, updated_at
            ) VALUES (
                :user_id, :bust_cm, :waist_cm, :hip_cm, :inseam_cm, :shoulder_cm,
                :shoe_eu, :fit_preference, :updated_at
            )
            ON CONFLICT(user_id) DO UPDATE SET
                bust_cm = excluded.bust_cm,
                waist_cm = excluded.waist_cm,
                hip_cm = excluded.hip_cm,
                inseam_cm = excluded.inseam_cm,
                shoulder_cm = excluded.shoulder_cm,
                shoe_eu = excluded.shoe_eu,
                fit_preference = excluded.fit_preference,
                updated_at = excluded.updated_at
            """,
            payload,
        )
    return payload


@router.get("/catalog")
def list_catalog(retailer_id: str | None = None) -> dict:
    with db() as connection:
        if retailer_id:
            rows = connection.execute(
                "SELECT * FROM catalog_products WHERE retailer_id = ? ORDER BY category, name",
                (retailer_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM catalog_products ORDER BY retailer_name, category, name"
            ).fetchall()
    return {"items": [decode_product(row) for row in rows]}


@router.post("/catalog")
def add_catalog_product(request: CatalogProductRequest) -> dict:
    product = {
        "id": str(uuid.uuid4()),
        "retailer_id": request.retailer_id,
        "retailer_name": request.retailer_name,
        "name": request.name,
        "category": request.category,
        "color": request.color,
        "price_eur": request.price_eur,
        "image_url": request.image_url,
        "product_url": request.product_url,
        "sizes_json": json.dumps(request.sizes),
        "size_chart_json": json.dumps(request.size_chart),
        "tags_json": json.dumps(request.tags),
        "created_at": utc_now(),
    }
    with db() as connection:
        connection.execute(
            """
            INSERT INTO catalog_products (
                id, retailer_id, retailer_name, name, category, color, price_eur,
                image_url, product_url, sizes_json, size_chart_json, tags_json, created_at
            ) VALUES (
                :id, :retailer_id, :retailer_name, :name, :category, :color, :price_eur,
                :image_url, :product_url, :sizes_json, :size_chart_json, :tags_json, :created_at
            )
            """,
            product,
        )
    return get_product(product["id"])


def relevant_measurements(category: str) -> list[str]:
    category = category.lower()
    if category in {"bottom", "bottoms", "jeans", "pants", "skirt"}:
        return ["waist", "hip", "inseam"]
    if category in {"shoes", "shoe", "sneakers", "boots"}:
        return ["shoe_eu"]
    if category in {"bag", "bags", "accessory", "accessories", "jewelry"}:
        return []
    return ["bust", "waist", "hip"]


def preference_adjustment(fit_preference: str) -> float:
    return {"slim": -1.0, "regular": 0.0, "relaxed": 2.0}.get(fit_preference, 0.0)


@router.post("/fit/recommend")
def recommend_fit(request: FitRecommendRequest) -> dict:
    profile = get_body_profile(request.user_id)
    product = get_product(request.product_id)
    measurements = relevant_measurements(product["category"])

    if not measurements:
        return {
            "product_id": product["id"],
            "recommended_size": product["sizes"][0] if product["sizes"] else "ONE SIZE",
            "confidence": 100,
            "basis": "one-size accessory",
            "notes": ["This item does not use body-size matching in the MVP."],
        }

    user_values = {
        "bust": profile.get("bust_cm"),
        "waist": profile.get("waist_cm"),
        "hip": profile.get("hip_cm"),
        "inseam": profile.get("inseam_cm"),
        "shoulder": profile.get("shoulder_cm"),
        "shoe_eu": profile.get("shoe_eu"),
    }
    available = [name for name in measurements if user_values.get(name) is not None]
    if not available:
        raise HTTPException(
            status_code=400,
            detail="Add the relevant body measurements before requesting a size recommendation.",
        )

    chart = product["size_chart"]
    if not chart:
        raise HTTPException(status_code=400, detail="This product has no size chart.")

    adjustment = preference_adjustment(profile.get("fit_preference", "regular"))
    scored: list[tuple[float, str, dict]] = []
    for size, target in chart.items():
        deltas = []
        detail = {}
        for name in available:
            if name not in target:
                continue
            user_value = float(user_values[name])
            target_value = float(target[name])
            if name != "shoe_eu":
                target_value += adjustment
            delta = target_value - user_value
            deltas.append(abs(delta))
            detail[name] = round(delta, 1)
        if deltas:
            scored.append((sum(deltas) / len(deltas), size, detail))

    if not scored:
        raise HTTPException(status_code=400, detail="The product size chart does not match the saved measurements.")

    scored.sort(key=lambda item: item[0])
    average_delta, recommended_size, detail = scored[0]
    completeness = len(detail) / max(1, len(measurements))
    confidence = int(max(45, min(96, 96 - average_delta * 5)) * completeness + 20 * (1 - completeness))

    notes = [
        f"Recommendation uses {', '.join(detail.keys())} measurements.",
        f"Fit preference: {profile.get('fit_preference', 'regular')}.",
        "This is a measurement-based recommendation, not a guarantee of physical fit; brand grading and fabric stretch can change the result.",
    ]
    return {
        "product_id": product["id"],
        "product_name": product["name"],
        "recommended_size": recommended_size,
        "confidence": confidence,
        "measurement_deltas_cm": detail,
        "basis": "saved measurements + retailer size chart",
        "notes": notes,
    }


@router.post("/catalog/complete-look")
def complete_look(request: CompleteLookRequest) -> dict:
    with db() as connection:
        rows = connection.execute("SELECT * FROM catalog_products").fetchall()
    products = [decode_product(row) for row in rows]
    anchor = get_product(request.anchor_product_id) if request.anchor_product_id else None

    preferred_categories = {
        "casual": ["top", "bottoms", "shoes", "bag"],
        "work": ["blazer", "top", "bottoms", "shoes", "bag"],
        "dinner": ["blazer", "top", "bottoms", "shoes", "bag"],
        "event": ["blazer", "top", "shoes", "bag"],
        "travel": ["top", "bottoms", "shoes", "bag"],
    }[request.occasion]

    anchor_color = (anchor or {}).get("color", "")
    selected: list[dict] = []
    running_total = 0.0
    for category in preferred_categories:
        candidates = [p for p in products if p["category"] == category and p["id"] != (anchor or {}).get("id")]
        if not candidates:
            continue

        def score(product: dict) -> tuple[int, float]:
            tags = set(product["tags"])
            occasion_score = 3 if request.occasion in tags else 0
            neutral_score = 2 if product["color"].lower() in {"black", "white", "cream", "ecru", "black and white"} else 0
            accent_score = 2 if anchor_color and product["color"].lower() == "burgundy" and anchor_color.lower() in {"black", "white", "black and white"} else 0
            return (occasion_score + neutral_score + accent_score, -product["price_eur"])

        choice = sorted(candidates, key=score, reverse=True)[0]
        if request.max_budget_eur is not None and running_total + choice["price_eur"] > request.max_budget_eur:
            continue
        selected.append(choice)
        running_total += choice["price_eur"]

    if anchor:
        selected.insert(0, anchor)
        running_total += anchor["price_eur"]

    return {
        "occasion": request.occasion,
        "items": selected,
        "total_eur": round(running_total, 2),
        "message": "Complete-look recommendations are generated from the connected retailer catalog. Demo products are used until a real catalog is ingested.",
    }


def fashn_headers() -> dict[str, str]:
    api_key = os.getenv("FASHN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="FASHN_API_KEY is not configured on the server.")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def submit_edit_job(source_image: str, prompt: str) -> str:
    privacy_mode = os.getenv("FIT360_PRIVATE_OUTPUT", "true").strip().lower() in {"1", "true", "yes"}
    payload = {
        "model_name": "edit",
        "inputs": {
            "image": source_image,
            "prompt": prompt,
            "resolution": "1k",
            "generation_mode": "fast",
            "output_format": "jpeg",
            "return_base64": privacy_mode,
        },
    }
    try:
        with httpx.Client(timeout=35.0) as client:
            response = client.post(f"{FASHN_BASE_URL}/run", json=payload, headers=fashn_headers())
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"FASHN edit request failed: {exc.response.text[:500]}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"FASHN edit request failed: {exc}") from exc

    prediction_id = data.get("id")
    if not prediction_id:
        raise HTTPException(status_code=502, detail="FASHN did not return a prediction id for the multi-view job.")
    return prediction_id


def extract_output(data: dict) -> str | None:
    output = data.get("output")
    if isinstance(output, list) and output:
        return output[0]
    if isinstance(output, dict):
        images = output.get("images")
        if isinstance(images, list) and images:
            return images[0]
    return None


@router.post("/multiview")
def create_multiview(request: MultiViewRequest) -> dict:
    provider = os.getenv("FIT360_VTON_PROVIDER", "mock").strip().lower()
    set_id = str(uuid.uuid4())
    now = utc_now()

    if provider != "fashn":
        outputs = {"front": request.source_image}
        with db() as connection:
            connection.execute(
                """
                INSERT INTO multiview_sets (
                    id, user_id, source_image, garment_name, provider, status,
                    jobs_json, outputs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    set_id,
                    request.user_id,
                    request.source_image,
                    request.garment_name,
                    "mock",
                    "mock",
                    json.dumps({}),
                    json.dumps(outputs),
                    now,
                    now,
                ),
            )
        return {
            "id": set_id,
            "status": "mock",
            "provider": "mock",
            "jobs": {},
            "outputs": outputs,
            "message": "360 beta is ready, but viewpoint generation needs FIT360_VTON_PROVIDER=fashn and a private FASHN_API_KEY.",
        }

    prompts = {
        "left_45": "Preserve the same person, face, hair, body proportions, outfit, garment details, lighting and background. Rotate the person to a natural 45-degree left three-quarter fashion view. Do not redesign the clothing.",
        "left_side": "Preserve the same person, identity, body proportions, outfit, garment details, lighting and background. Show a clean full-body left side profile, as a fashion fit reference. Do not redesign the clothing.",
        "back": "Preserve the same person, body proportions, outfit, garment details, lighting and background. Turn the person around and show a clean full-body back view of the exact same outfit. Keep garment construction consistent.",
        "right_side": "Preserve the same person, identity, body proportions, outfit, garment details, lighting and background. Show a clean full-body right side profile, as a fashion fit reference. Do not redesign the clothing.",
        "right_45": "Preserve the same person, face, hair, body proportions, outfit, garment details, lighting and background. Rotate the person to a natural 45-degree right three-quarter fashion view. Do not redesign the clothing.",
    }
    jobs = {angle: submit_edit_job(request.source_image, prompt) for angle, prompt in prompts.items()}
    outputs = {"front": request.source_image}

    with db() as connection:
        connection.execute(
            """
            INSERT INTO multiview_sets (
                id, user_id, source_image, garment_name, provider, status,
                jobs_json, outputs_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                set_id,
                request.user_id,
                request.source_image,
                request.garment_name,
                "fashn",
                "processing",
                json.dumps(jobs),
                json.dumps(outputs),
                now,
                now,
            ),
        )

    return {
        "id": set_id,
        "status": "processing",
        "provider": "fashn",
        "jobs": jobs,
        "outputs": outputs,
        "message": "Generating consistent fashion viewpoints. This is an AI 360 beta, not geometry-accurate 3D cloth simulation.",
    }


@router.get("/multiview/{set_id}")
def multiview_status(set_id: str) -> dict:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM multiview_sets WHERE id = ?",
            (set_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Multi-view set not found")

    item = dict(row)
    jobs = json.loads(item["jobs_json"])
    outputs = json.loads(item["outputs_json"])
    if item["provider"] == "mock" or not jobs:
        return {
            "id": set_id,
            "status": item["status"],
            "provider": item["provider"],
            "outputs": outputs,
            "pending": [],
            "failed": {},
        }

    headers = fashn_headers()
    pending: list[str] = []
    failed: dict[str, str] = {}
    for angle, prediction_id in jobs.items():
        if angle in outputs:
            continue
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(f"{FASHN_BASE_URL}/status/{prediction_id}", headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            failed[angle] = exc.response.text[:300]
            continue
        except httpx.HTTPError as exc:
            failed[angle] = str(exc)
            continue

        status = data.get("status", "unknown")
        if status == "completed":
            result = extract_output(data)
            if result:
                outputs[angle] = result
            else:
                failed[angle] = "Completed without an image output"
        elif status in {"starting", "in_queue", "processing", "queued"}:
            pending.append(angle)
        else:
            failed[angle] = str(data.get("error") or status)

    status = "completed" if not pending and not failed and len(outputs) >= len(jobs) + 1 else "processing"
    if failed and not pending:
        status = "partial" if len(outputs) > 1 else "failed"

    with db() as connection:
        connection.execute(
            "UPDATE multiview_sets SET status = ?, outputs_json = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(outputs), utc_now(), set_id),
        )

    return {
        "id": set_id,
        "status": status,
        "provider": item["provider"],
        "outputs": outputs,
        "pending": pending,
        "failed": failed,
    }


@router.get("/multiview/user/{user_id}/latest")
def latest_multiview(user_id: str) -> dict:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM multiview_sets WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if not row:
        return {"item": None}
    item = dict(row)
    item["jobs"] = json.loads(item.pop("jobs_json"))
    item["outputs"] = json.loads(item.pop("outputs_json"))
    return {"item": item}
