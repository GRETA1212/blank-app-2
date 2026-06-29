from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from character_lab import load_character
from object_storage import StorageError, publish_reference_image
from providers import (
    ElevenLabsVoiceProvider,
    HeyGenVideoProvider,
    JobStatus,
    ProviderError,
    ProviderJob,
    RunwayVideoProvider,
    VideoRequest,
    VoiceRequest,
)
from providers.http_client import HttpClient
from realism_pipeline import RealismProject, build_realism_manifest, ensure_project_structure, load_project


PROVIDER_COST_EUR_PER_SECOND = {
    "heygen": 0.067,
    "runway": 0.05,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def provider_readiness() -> list[dict[str, Any]]:
    runway = RunwayVideoProvider()
    heygen = HeyGenVideoProvider()
    elevenlabs = ElevenLabsVoiceProvider()
    return [
        {
            "provider": "HeyGen",
            "key": "heygen",
            "role": "Talking creator shots",
            "configured": heygen.configured,
            "estimated_eur_per_second": PROVIDER_COST_EUR_PER_SECOND["heygen"],
            "missing": [] if heygen.configured else ["HEYGEN_API_KEY", "HEYGEN_AVATAR_ID"],
        },
        {
            "provider": "Runway",
            "key": "runway",
            "role": "Lifestyle and B-roll shots",
            "configured": runway.configured,
            "estimated_eur_per_second": PROVIDER_COST_EUR_PER_SECOND["runway"],
            "missing": [] if runway.configured else ["RUNWAYML_API_SECRET"],
        },
        {
            "provider": "ElevenLabs",
            "key": "elevenlabs",
            "role": "Licensed or consented voice",
            "configured": elevenlabs.configured,
            "estimated_eur_per_second": None,
            "missing": [] if elevenlabs.configured else ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"],
        },
    ]


def _require_rights(project: RealismProject) -> None:
    blockers = project.rights.hard_blockers()
    if blockers:
        raise ProviderError("Generation blocked by rights gate: " + " ".join(blockers))


def _route_provider(shot_number: int, dialogue: str) -> tuple[str, str]:
    talking_shot = shot_number % 2 == 1 and bool(dialogue.strip())
    return ("heygen", "talking_creator") if talking_shot else ("runway", "lifestyle_broll")


def build_generation_plan(project: RealismProject) -> dict[str, Any]:
    _require_rights(project)
    character = load_character(project.character_name)
    manifest = build_realism_manifest(project, character)
    shots: list[dict[str, Any]] = []

    for item in manifest["shots"]:
        shot_number = int(item["shot_number"])
        provider, purpose = _route_provider(shot_number, item.get("dialogue", ""))
        duration = float(item["duration_seconds"])
        shots.append(
            {
                "shot_number": shot_number,
                "title": item["title"],
                "provider": provider,
                "purpose": purpose,
                "duration_seconds": duration,
                "estimated_cost_eur": round(duration * PROVIDER_COST_EUR_PER_SECOND[provider], 2),
                "script": item.get("dialogue", "") if provider == "heygen" else None,
                "prompt": item["visual_prompt"],
                "negative_prompt": item["negative_prompt"],
                "requires_reference_image_url": provider == "runway",
                "status": "READY_TO_SUBMIT",
            }
        )

    plan = {
        "schema_version": 2,
        "project_id": project.project_id,
        "character": project.character_name,
        "created_at": _now(),
        "rights_approved": True,
        "strategy": "Talking shots use HeyGen; lifestyle and B-roll shots use Runway. Each shot stays replaceable.",
        "estimated_total_cost_eur": round(sum(item["estimated_cost_eur"] for item in shots), 2),
        "shots": shots,
    }
    path = ensure_project_structure(project.project_id)["manifests"] / "provider_generation_plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def _jobs_path(project_id: str) -> Path:
    return ensure_project_structure(project_id)["manifests"] / "provider_jobs.json"


def load_provider_jobs(project_id: str) -> list[dict[str, Any]]:
    path = _jobs_path(project_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _save_job_record(project_id: str, shot_number: int, job: ProviderJob) -> dict[str, Any]:
    records = load_provider_jobs(project_id)
    record = {
        "id": f"{job.provider}:{job.job_id}",
        "project_id": project_id,
        "shot_number": int(shot_number),
        "provider": job.provider,
        "provider_job_id": job.job_id,
        "status": job.status.value,
        "output_url": job.output_url,
        "error": job.error,
        "updated_at": _now(),
        "raw": job.raw,
    }
    index = next((i for i, item in enumerate(records) if item.get("id") == record["id"]), None)
    if index is None:
        record["created_at"] = record["updated_at"]
        records.append(record)
    else:
        record["created_at"] = records[index].get("created_at", record["updated_at"])
        records[index] = record
    _jobs_path(project_id).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def _video_provider(name: str):
    if name == "heygen":
        return HeyGenVideoProvider()
    if name == "runway":
        return RunwayVideoProvider()
    raise ProviderError(f"Unsupported video provider: {name}")


def submit_shot_job(
    project_id: str,
    shot_number: int,
    provider_name: str,
    *,
    reference_image_url: str | None = None,
    avatar_id: str | None = None,
    voice_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    project = load_project(project_id)
    _require_rights(project)
    plan = build_generation_plan(project)
    planned = next((item for item in plan["shots"] if item["shot_number"] == int(shot_number)), None)
    if planned is None:
        raise ProviderError(f"Shot {shot_number} does not exist.")

    provider = _video_provider(provider_name)
    request = VideoRequest(
        project_id=project.project_id,
        shot_number=int(shot_number),
        title=f"{project.character_name} — {planned['title']}",
        prompt=planned["prompt"],
        script=planned.get("script"),
        duration_seconds=int(round(float(planned["duration_seconds"]))),
        aspect_ratio="9:16",
        reference_image_url=reference_image_url,
        avatar_id=avatar_id,
        voice_id=voice_id,
        model=model,
        metadata={"character": project.character_name, "topic": project.topic},
    )
    return _save_job_record(project_id, shot_number, provider.create_video(request))


def submit_all_shots(
    project_id: str,
    *,
    reference_image_url: str | None = None,
    publish_local_reference: bool = True,
) -> dict[str, Any]:
    project = load_project(project_id)
    _require_rights(project)
    plan = build_generation_plan(project)
    existing = load_provider_jobs(project_id)
    active_shots = {
        int(item["shot_number"])
        for item in existing
        if item.get("status") in {JobStatus.QUEUED.value, JobStatus.PROCESSING.value, JobStatus.SUCCEEDED.value}
    }
    needs_reference = any(item["requires_reference_image_url"] and item["shot_number"] not in active_shots for item in plan["shots"])
    if needs_reference and not reference_image_url and publish_local_reference:
        try:
            reference_image_url = publish_reference_image(project_id, expires_seconds=7200)
        except StorageError as error:
            raise ProviderError(str(error)) from error
    submitted: list[dict[str, Any]] = []
    skipped: list[int] = []
    errors: list[dict[str, Any]] = []
    for shot in plan["shots"]:
        number = int(shot["shot_number"])
        if number in active_shots:
            skipped.append(number)
            continue
        try:
            submitted.append(
                submit_shot_job(
                    project_id,
                    number,
                    shot["provider"],
                    reference_image_url=reference_image_url if shot["provider"] == "runway" else None,
                )
            )
        except ProviderError as error:
            errors.append({"shot_number": number, "provider": shot["provider"], "error": str(error)})
    return {"submitted": submitted, "skipped": skipped, "errors": errors, "reference_image_url": reference_image_url}


def refresh_shot_job(project_id: str, provider_name: str, provider_job_id: str, shot_number: int) -> dict[str, Any]:
    project = load_project(project_id)
    _require_rights(project)
    provider = _video_provider(provider_name)
    return _save_job_record(project_id, shot_number, provider.get_job(provider_job_id))


def refresh_all_jobs(project_id: str) -> dict[str, Any]:
    refreshed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for record in load_provider_jobs(project_id):
        if record.get("status") in {JobStatus.SUCCEEDED.value, JobStatus.FAILED.value}:
            continue
        try:
            refreshed.append(
                refresh_shot_job(
                    project_id,
                    str(record["provider"]),
                    str(record["provider_job_id"]),
                    int(record["shot_number"]),
                )
            )
        except ProviderError as error:
            errors.append({"id": record.get("id"), "error": str(error)})
    return {"refreshed": refreshed, "errors": errors}


def generate_shot_voice(project_id: str, shot_number: int) -> Path:
    project = load_project(project_id)
    _require_rights(project)
    if not project.rights.voice_is_licensed_or_consented:
        raise ProviderError("Voice generation is blocked until voice rights are confirmed.")
    shot = next((item for item in project.shots if item.shot_number == int(shot_number)), None)
    if shot is None:
        raise ProviderError(f"Shot {shot_number} does not exist.")
    provider = ElevenLabsVoiceProvider()
    output = ensure_project_structure(project_id)["audio"] / f"shot-{int(shot_number):02d}-voice.mp3"
    return provider.synthesize(VoiceRequest(text=shot.dialogue), output)


def generate_all_voices(project_id: str) -> dict[str, Any]:
    project = load_project(project_id)
    _require_rights(project)
    created: list[str] = []
    errors: list[dict[str, Any]] = []
    for shot in project.shots:
        if not shot.dialogue.strip():
            continue
        try:
            created.append(str(generate_shot_voice(project_id, shot.shot_number)))
        except ProviderError as error:
            errors.append({"shot_number": shot.shot_number, "error": str(error)})
    return {"created": created, "errors": errors}


def save_completed_video(project_id: str, record_id: str, http: HttpClient | None = None) -> Path:
    records = load_provider_jobs(project_id)
    record = next((item for item in records if item.get("id") == record_id), None)
    if record is None:
        raise ProviderError("Generation job was not found.")
    if record.get("status") != JobStatus.SUCCEEDED.value or not record.get("output_url"):
        raise ProviderError("The provider job is not complete yet.")
    url = str(record["output_url"])
    if not url.startswith("https://"):
        raise ProviderError("Provider output must use HTTPS.")
    payload = (http or HttpClient()).request_bytes("GET", url, timeout=300)
    if not payload:
        raise ProviderError("The provider returned an empty video file.")
    destination = ensure_project_structure(project_id)["generated_shots"] / f"{int(record['shot_number']):02d}-{record['provider']}.mp4"
    destination.write_bytes(payload)
    return destination


def save_all_completed(project_id: str) -> dict[str, Any]:
    saved: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, Any]] = []
    for record in load_provider_jobs(project_id):
        destination = ensure_project_structure(project_id)["generated_shots"] / f"{int(record['shot_number']):02d}-{record['provider']}.mp4"
        if destination.exists():
            skipped.append(str(destination))
            continue
        if record.get("status") != JobStatus.SUCCEEDED.value:
            continue
        try:
            saved.append(str(save_completed_video(project_id, str(record["id"]))))
        except ProviderError as error:
            errors.append({"id": record.get("id"), "error": str(error)})
    return {"saved": saved, "skipped": skipped, "errors": errors}
