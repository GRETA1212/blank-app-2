from pathlib import Path
import zipfile

import pytest

from character_lab import clone_default_character
from realism_pipeline import (
    RealismProject,
    RightsRecord,
    build_realism_manifest,
    default_shot_plan,
    evaluate_realism_gate,
    export_project_package,
    generate_srt,
    load_project,
    safe_project_id,
    save_project,
    save_project_asset,
    utc_now_iso,
    validate_media,
)


def full_rights() -> RightsRecord:
    return RightsRecord(
        actor_consent=True,
        face_identity_is_fictional_or_authorized=True,
        voice_is_licensed_or_consented=True,
        property_and_product_media_authorized=True,
        ai_disclosure_required=True,
    )


def test_default_realism_plan_uses_short_controlled_shots() -> None:
    sofia = clone_default_character("Sofia")
    shots = default_shot_plan(sofia, "eyeliner placement")

    assert len(shots) == 5
    assert all(2 <= shot.duration_seconds <= 8 for shot in shots)
    assert shots[0].action_name in [item["name"] for item in sofia.actions]
    assert shots[0].location_name in [item["name"] for item in sofia.locations]


def test_project_round_trip(tmp_path: Path) -> None:
    luna = clone_default_character("Luna")
    project = RealismProject(
        project_id=safe_project_id("Luna", "message from tomorrow"),
        character_name="Luna",
        topic="message from tomorrow",
        workflow_mode="Actor performance + fictional identity transfer",
        target_language="English",
        platform="TikTok",
        created_at=utc_now_iso(),
        rights=full_rights(),
        shots=default_shot_plan(luna, "message from tomorrow"),
    )

    save_project(project, tmp_path)
    loaded = load_project(project.project_id, tmp_path)

    assert loaded.character_name == "Luna"
    assert len(loaded.shots) == 5
    assert loaded.rights.voice_is_licensed_or_consented is True


def test_media_validation_and_safe_storage(tmp_path: Path) -> None:
    path = save_project_asset(
        "sofia-test",
        "generated_shot",
        "../../shot clip.MP4",
        b"fake-video",
        shot_number=2,
        storage_root=tmp_path,
    )
    assert path.name == "02-shot-clip.mp4"
    assert path.exists()

    with pytest.raises(ValueError):
        validate_media("malware.exe", b"x", "performance_video")


def test_manifest_contains_hybrid_realism_stages() -> None:
    elena = clone_default_character("Elena")
    project = RealismProject(
        project_id="elena-realism",
        character_name="Elena",
        topic="small apartment tour",
        workflow_mode="Actor performance + fictional identity transfer",
        target_language="Italian",
        platform="TikTok + YouTube Shorts",
        created_at=utc_now_iso(),
        rights=full_rights(),
        shots=default_shot_plan(elena, "small apartment tour"),
    )

    manifest = build_realism_manifest(project, elena)

    assert manifest["rights_status"]["approved"] is True
    assert len(manifest["stages"]) == 5
    assert manifest["shots"][0]["performance_direction"]
    assert manifest["shots"][0]["voice_direction"]
    assert "celebrity likeness" in manifest["shots"][0]["negative_prompt"]


def test_srt_timing_uses_shot_durations() -> None:
    sofia = clone_default_character("Sofia")
    shots = default_shot_plan(sofia, "soft glam")
    srt = generate_srt(shots)

    assert "00:00:00,000 --> 00:00:05,000" in srt
    assert "00:00:20,000 --> 00:00:26,000" in srt
    assert shots[0].dialogue in srt


def test_package_contains_manifest_subtitles_and_review_checklist(tmp_path: Path) -> None:
    luna = clone_default_character("Luna")
    project = RealismProject(
        project_id="luna-package",
        character_name="Luna",
        topic="future message",
        workflow_mode="Actor performance + fictional identity transfer",
        target_language="English",
        platform="YouTube Shorts",
        created_at=utc_now_iso(),
        rights=full_rights(),
        shots=default_shot_plan(luna, "future message"),
    )

    archive = export_project_package(project, luna, tmp_path)

    assert archive.exists()
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
    assert "manifests/realism_manifest.json" in names
    assert "subtitles/subtitles.srt" in names
    assert "project.json" in names
    assert "manifests/human_review_checklist.txt" in names


def test_reality_gate_blocks_missing_consent_even_when_visual_checks_pass() -> None:
    rights = full_rights()
    rights.actor_consent = False
    result = evaluate_realism_gate(
        {"face": True, "motion": True, "voice": True},
        rights,
    )

    assert result["score"] == 100.0
    assert result["status"] == "BLOCKED — RIGHTS OR CONSENT"
    assert result["hard_blockers"]
