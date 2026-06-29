from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from creator_studio import SEED_CHARACTERS, generate_video_plan


DATA_FILE = Path("storage/creator_os.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def blank_data() -> dict[str, Any]:
    return {
        "trends": [],
        "ideas": [],
        "calendar": [],
        "publications": [],
        "analytics": [],
        "income": [],
        "settings": {
            "default_character": "Sofia",
            "default_platform": "TikTok + YouTube Shorts",
            "default_language": "English",
            "daily_video_target": 1,
        },
    }


def load_data() -> dict[str, Any]:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        data = blank_data()
        save_data(data)
        return data
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = blank_data()
    defaults = blank_data()
    for key, value in defaults.items():
        data.setdefault(key, value)
    return data


def save_data(data: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def add_trends(data: dict[str, Any], trends: list[dict[str, Any]]) -> int:
    existing = {(item.get("source"), item.get("title", "").lower(), item.get("region")) for item in data["trends"]}
    added = 0
    for trend in trends:
        key = (trend.get("source"), str(trend.get("title", "")).lower(), trend.get("region"))
        if key in existing:
            continue
        data["trends"].append(trend)
        existing.add(key)
        added += 1
    data["trends"] = sorted(data["trends"], key=lambda item: float(item.get("score", 0)), reverse=True)[:500]
    save_data(data)
    return added


def top_trends(data: dict[str, Any], *, niche: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    items = data["trends"]
    if niche:
        items = [item for item in items if item.get("niche") == niche]
    return sorted(items, key=lambda item: float(item.get("score", 0)), reverse=True)[:limit]


def _historical_fit(data: dict[str, Any], character: str) -> float:
    records = [item for item in data["analytics"] if item.get("character") == character]
    if not records:
        return 50.0
    scores = [float(item.get("growth_score", 0)) for item in records[-20:] if item.get("growth_score") is not None]
    return round(sum(scores) / len(scores), 1) if scores else 50.0


def _blocked_topic(title: str, avoid_topics: list[str]) -> bool:
    lowered = title.lower()
    return any(item.lower() in lowered for item in avoid_topics if item.strip())


def create_daily_ideas(
    data: dict[str, Any],
    *,
    character: str,
    language: str,
    platform: str,
    planned_date: date,
    count: int = 3,
    niche_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    profile = SEED_CHARACTERS[character]
    niche_profile = dict(niche_profile or {})
    active_niche = str(niche_profile.get("primary_niche") or profile.niche)
    avoid_topics = [str(item) for item in niche_profile.get("avoid_topics", [])]
    candidates = [
        item
        for item in top_trends(data, niche=active_niche, limit=max(count * 6, 15))
        if not _blocked_topic(str(item.get("title", "")), avoid_topics)
    ]
    if not candidates:
        candidates = [
            {
                "id": f"seed-{index}",
                "title": series,
                "source": "Signature series",
                "score": 60.0,
                "niche": active_niche,
                "url": None,
            }
            for index, series in enumerate(profile.signature_series, start=1)
            if not _blocked_topic(series, avoid_topics)
        ]

    created: list[dict[str, Any]] = []
    history_fit = _historical_fit(data, character)
    for trend in candidates[: max(1, min(int(count), 10))]:
        topic = str(trend["title"])
        plan = generate_video_plan(
            profile,
            topic,
            language,
            30,
            "Views + monetization",
            platform,
        )
        idea = {
            "id": _id("idea"),
            "created_at": _now(),
            "planned_date": planned_date.isoformat(),
            "character": character,
            "niche": active_niche,
            "topic": topic,
            "trend_id": trend.get("id"),
            "trend_source": trend.get("source"),
            "trend_url": trend.get("url"),
            "trend_score": float(trend.get("score", 0)),
            "historical_fit": history_fit,
            "platform": platform,
            "language": language,
            "status": "PROPOSED",
            "audience": niche_profile.get("audience", profile.audience),
            "content_pillars": list(niche_profile.get("content_pillars", [])),
            "products": list(niche_profile.get("products", [])),
            "avoid_topics": avoid_topics,
            "plan": plan,
        }
        data["ideas"].append(idea)
        created.append(idea)
    save_data(data)
    return created


def approve_idea(data: dict[str, Any], idea_id: str) -> dict[str, Any]:
    idea = next((item for item in data["ideas"] if item.get("id") == idea_id), None)
    if idea is None:
        raise KeyError(f"Idea not found: {idea_id}")
    idea["status"] = "APPROVED"
    scheduled = next((item for item in data["calendar"] if item.get("idea_id") == idea_id), None)
    if scheduled is None:
        scheduled = {
            "id": _id("slot"),
            "idea_id": idea_id,
            "character": idea["character"],
            "title": idea["topic"],
            "platform": idea["platform"],
            "date": idea["planned_date"],
            "status": "PLANNED",
            "video_id": None,
            "project_id": None,
            "created_at": _now(),
        }
        data["calendar"].append(scheduled)
    save_data(data)
    return scheduled


def link_calendar_video(data: dict[str, Any], idea_id: str, video_id: str, project_id: str | None = None) -> dict[str, Any]:
    slot = next((item for item in data["calendar"] if item.get("idea_id") == idea_id), None)
    if slot is None:
        raise KeyError(f"Calendar slot not found for idea: {idea_id}")
    slot["video_id"] = video_id
    slot["project_id"] = project_id
    slot["status"] = "IN_PRODUCTION" if project_id else "QUEUED"
    save_data(data)
    return slot


def record_publication(
    data: dict[str, Any],
    *,
    video_id: str,
    platform: str,
    external_id: str | None,
    url: str | None,
    status: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "id": _id("publication"),
        "video_id": video_id,
        "platform": platform,
        "external_id": external_id,
        "url": url,
        "status": status,
        "metadata": dict(metadata or {}),
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["publications"].append(record)
    save_data(data)
    return record


def record_analytics(data: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    saved = dict(record)
    saved.setdefault("id", _id("analytics"))
    saved.setdefault("recorded_at", _now())
    data["analytics"].append(saved)
    save_data(data)
    return saved


def record_income(
    data: dict[str, Any],
    *,
    character: str,
    source: str,
    amount_eur: float,
    occurred_on: date,
    video_id: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    item = {
        "id": _id("income"),
        "character": character,
        "source": source,
        "amount_eur": float(amount_eur),
        "date": occurred_on.isoformat(),
        "video_id": video_id,
        "note": note.strip(),
        "created_at": _now(),
    }
    data["income"].append(item)
    save_data(data)
    return item


def calendar_range(data: dict[str, Any], start: date, days: int = 30) -> list[dict[str, Any]]:
    end = start + timedelta(days=max(1, days))
    return sorted(
        [item for item in data["calendar"] if start.isoformat() <= item.get("date", "") < end.isoformat()],
        key=lambda item: (item.get("date", ""), item.get("character", "")),
    )


def revenue_summary(data: dict[str, Any]) -> dict[str, Any]:
    total = sum(float(item.get("amount_eur", 0)) for item in data["income"])
    by_source: dict[str, float] = {}
    by_character: dict[str, float] = {}
    for item in data["income"]:
        amount = float(item.get("amount_eur", 0))
        by_source[item.get("source", "Other")] = by_source.get(item.get("source", "Other"), 0.0) + amount
        by_character[item.get("character", "Unknown")] = by_character.get(item.get("character", "Unknown"), 0.0) + amount
    return {
        "total_eur": round(total, 2),
        "by_source": {key: round(value, 2) for key, value in by_source.items()},
        "by_character": {key: round(value, 2) for key, value in by_character.items()},
    }
