from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from character_lab import load_character
from creator_studio import calculate_growth_score, recommend_action
from realism_pipeline import RealismProject, RightsRecord, default_shot_plan, load_project, safe_project_id, save_project, utc_now_iso

DATA_FILE = Path("storage/personal_creator_hq.json")
VIDEO_STATUSES = ["QUEUE", "SCRIPTED", "IN_PRODUCTION", "RENDERING", "REVIEW", "READY", "PUBLISHED", "PAUSED"]
PROJECT_STATUS_MAP = {"PLANNING": "SCRIPTED", "DIRECTED": "IN_PRODUCTION", "RENDERING": "RENDERING", "RENDERED": "READY", "APPROVED": "READY"}


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def blank_data() -> dict[str, Any]:
    return {"owner": "Greta Bafqari", "monthly_goal": 1000, "accounts": [], "videos": [], "income": [], "tests": []}


def save_data(data: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(DATA_FILE)


def load_data() -> dict[str, Any]:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = blank_data()
    else:
        data = blank_data()
    changed = False
    for key, value in blank_data().items():
        if key not in data:
            data[key] = value
            changed = True
    legacy = {"Idea": "QUEUE", "Scripted": "SCRIPTED", "Producing": "IN_PRODUCTION", "Ready": "READY", "Published": "PUBLISHED", "Paused": "PAUSED"}
    for account in data["accounts"]:
        if not account.get("id"):
            account["id"] = _id("account")
            changed = True
    for video in data["videos"]:
        if not video.get("id"):
            video["id"] = _id("video")
            changed = True
        status = legacy.get(video.get("status", "QUEUE"), video.get("status", "QUEUE"))
        video["status"] = status if status in VIDEO_STATUSES else "QUEUE"
        video.setdefault("project_id", None)
        video.setdefault("rendered_path", None)
        video.setdefault("published_url", None)
        video.setdefault("analytics_id", None)
        video.setdefault("production_cost_eur", 0.0)
        video.setdefault("created_at", _now())
        changed = sync_video(data, video) or changed
    if changed:
        save_data(data)
    return data


def find_video(data: dict[str, Any], video_id: str) -> dict[str, Any]:
    result = next((item for item in data["videos"] if item.get("id") == video_id), None)
    if result is None:
        raise KeyError(f"Video not found: {video_id}")
    return result


def add_video(data: dict[str, Any], character: str, title: str, platform: str, planned_date: date, objective: str, language: str, cost: float) -> dict[str, Any]:
    video = {
        "id": _id("video"), "character": character, "title": title.strip(), "platform": platform,
        "status": "QUEUE", "planned_date": planned_date.isoformat(), "objective": objective,
        "language": language, "production_cost_eur": float(cost), "created_at": _now(),
        "project_id": None, "rendered_path": None, "published_url": None, "analytics_id": None,
    }
    data["videos"].append(video)
    save_data(data)
    return video


def start_production(data: dict[str, Any], video_id: str) -> RealismProject:
    video = find_video(data, video_id)
    if video.get("project_id"):
        try:
            return load_project(video["project_id"])
        except FileNotFoundError:
            pass
    character = load_character(video["character"])
    project = RealismProject(
        project_id=safe_project_id(video["character"], video["title"]),
        character_name=video["character"], topic=video["title"],
        workflow_mode="Actor performance + fictional identity transfer",
        target_language=video.get("language", "English"), platform=video.get("platform", "TikTok + YouTube Shorts"),
        created_at=utc_now_iso(),
        rights=RightsRecord(False, False, False, False, True, f"Started from HQ video {video['id']}"),
        shots=default_shot_plan(character, video["title"]), status="PLANNING",
    )
    save_project(project)
    video["project_id"] = project.project_id
    video["status"] = "SCRIPTED"
    save_data(data)
    return project


def sync_video(data: dict[str, Any], video: dict[str, Any]) -> bool:
    project_id = video.get("project_id")
    if not project_id:
        return False
    try:
        project = load_project(project_id)
    except Exception:
        return False
    changed = False
    mapped = PROJECT_STATUS_MAP.get(project.status)
    if mapped and video.get("status") != "PUBLISHED" and video.get("status") != mapped:
        video["status"] = mapped
        changed = True
    rendered = Path("storage") / "realism_projects" / project_id / "exports" / f"{project_id}-master.mp4"
    if rendered.exists() and video.get("rendered_path") != str(rendered):
        video["rendered_path"] = str(rendered)
        if video.get("status") != "PUBLISHED":
            video["status"] = "READY"
        changed = True
    return changed


def mark_published(data: dict[str, Any], video_id: str, url: str, published_date: date) -> dict[str, Any]:
    video = find_video(data, video_id)
    video["status"] = "PUBLISHED"
    video["published_url"] = url.strip()
    video["published_date"] = published_date.isoformat()
    save_data(data)
    return video


def save_analytics(data: dict[str, Any], video_id: str, views: int, retention: float, completion: float, shares: int, followers: int, revenue: float, cost: float) -> dict[str, Any]:
    video = find_video(data, video_id)
    growth = calculate_growth_score(retention, completion, shares / views * 1000 if views else 0.0, followers / views * 1000 if views else 0.0)
    profit = round(float(revenue) - float(cost), 2)
    record = {
        "id": video.get("analytics_id") or _id("test"), "video_id": video_id,
        "character": video["character"], "topic": video["title"], "views": int(views),
        "retention_percent": float(retention), "completion_percent": float(completion),
        "shares": int(shares), "followers_gained": int(followers), "growth_score": growth,
        "revenue_eur": float(revenue), "cost_eur": float(cost), "profit_eur": profit,
        "decision": recommend_action(growth, profit, int(views)), "recorded_at": _now(),
    }
    index = next((i for i, item in enumerate(data["tests"]) if item.get("id") == record["id"]), None)
    if index is None:
        data["tests"].append(record)
    else:
        data["tests"][index] = record
    video["analytics_id"] = record["id"]
    save_data(data)
    return record
