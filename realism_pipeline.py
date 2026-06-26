from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from character_lab import CharacterDNA, build_scene_direction, character_to_dict, slugify as character_slugify


VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 100 * 1024 * 1024


@dataclass
class RightsRecord:
    actor_consent: bool
    face_identity_is_fictional_or_authorized: bool
    voice_is_licensed_or_consented: bool
    property_and_product_media_authorized: bool
    ai_disclosure_required: bool
    notes: str = ""

    def hard_blockers(self) -> list[str]:
        blockers: list[str] = []
        if not self.actor_consent:
            blockers.append("Actor/performance consent is not confirmed.")
        if not self.face_identity_is_fictional_or_authorized:
            blockers.append("The digital face is not confirmed as fictional or authorized.")
        if not self.voice_is_licensed_or_consented:
            blockers.append("Voice rights are not confirmed.")
        if not self.property_and_product_media_authorized:
            blockers.append("Property/product/background media rights are not confirmed.")
        return blockers


@dataclass
class ShotSpec:
    shot_number: int
    title: str
    duration_seconds: float
    dialogue: str
    emotion: str
    action_name: str
    location_name: str
    wardrobe_name: str
    camera: str
    performance_source: str = "Consenting actor performance"
    notes: str = ""


@dataclass
class RealismProject:
    project_id: str
    character_name: str
    topic: str
    workflow_mode: str
    target_language: str
    platform: str
    created_at: str
    rights: RightsRecord
    shots: list[ShotSpec] = field(default_factory=list)
    status: str = "PLANNING"

    @property
    def total_duration_seconds(self) -> float:
        return round(sum(shot.duration_seconds for shot in self.shots), 2)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_project_id(character_name: str, topic: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{character_slugify(character_name)}-{character_slugify(topic)}-{stamp}"


def project_directory(project_id: str, storage_root: Path | str = "storage") -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", project_id).strip("-")
    if not safe_id:
        raise ValueError("Project ID cannot be empty.")
    return Path(storage_root) / "realism_projects" / safe_id


def ensure_project_structure(project_id: str, storage_root: Path | str = "storage") -> dict[str, Path]:
    root = project_directory(project_id, storage_root)
    paths = {
        "root": root,
        "performance": root / "performance",
        "identity": root / "identity",
        "voice": root / "voice",
        "generated_shots": root / "generated_shots",
        "audio": root / "audio",
        "subtitles": root / "subtitles",
        "exports": root / "exports",
        "manifests": root / "manifests",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _clean_filename(filename: str) -> str:
    raw = Path(filename).name
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(raw).stem).strip("-") or "asset"
    return f"{stem}{Path(raw).suffix.lower()}"


def validate_media(filename: str, payload: bytes, media_kind: str) -> None:
    if not payload:
        raise ValueError("Uploaded file is empty.")
    suffix = Path(filename).suffix.lower()
    rules = {
        "performance_video": (VIDEO_EXTENSIONS, MAX_VIDEO_BYTES, "video"),
        "generated_shot": (VIDEO_EXTENSIONS, MAX_VIDEO_BYTES, "video"),
        "identity_image": (IMAGE_EXTENSIONS, MAX_IMAGE_BYTES, "image"),
        "voice_sample": (AUDIO_EXTENSIONS, MAX_AUDIO_BYTES, "audio"),
        "narration_audio": (AUDIO_EXTENSIONS, MAX_AUDIO_BYTES, "audio"),
    }
    if media_kind not in rules:
        raise ValueError(f"Unsupported media kind: {media_kind}")
    allowed, maximum, label = rules[media_kind]
    if suffix not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValueError(f"{label.title()} must use one of these extensions: {allowed_text}")
    if len(payload) > maximum:
        raise ValueError(f"{label.title()} exceeds the allowed file-size limit.")


def save_project_asset(
    project_id: str,
    media_kind: str,
    filename: str,
    payload: bytes,
    *,
    storage_root: Path | str = "storage",
    shot_number: int | None = None,
) -> Path:
    validate_media(filename, payload, media_kind)
    paths = ensure_project_structure(project_id, storage_root)
    target_folder = {
        "performance_video": paths["performance"],
        "identity_image": paths["identity"],
        "voice_sample": paths["voice"],
        "generated_shot": paths["generated_shots"],
        "narration_audio": paths["audio"],
    }[media_kind]
    clean_name = _clean_filename(filename)
    if media_kind == "generated_shot":
        if shot_number is None or shot_number < 1:
            raise ValueError("Generated shot assets require a positive shot number.")
        clean_name = f"{shot_number:02d}-{clean_name}"
    destination = target_folder / clean_name
    destination.write_bytes(payload)
    return destination


def save_project(project: RealismProject, storage_root: Path | str = "storage") -> Path:
    paths = ensure_project_structure(project.project_id, storage_root)
    destination = paths["root"] / "project.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(asdict(project), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def project_from_dict(data: dict[str, Any]) -> RealismProject:
    return RealismProject(
        project_id=data["project_id"],
        character_name=data["character_name"],
        topic=data["topic"],
        workflow_mode=data["workflow_mode"],
        target_language=data["target_language"],
        platform=data["platform"],
        created_at=data["created_at"],
        rights=RightsRecord(**data["rights"]),
        shots=[ShotSpec(**shot) for shot in data.get("shots", [])],
        status=data.get("status", "PLANNING"),
    )


def load_project(project_id: str, storage_root: Path | str = "storage") -> RealismProject:
    path = project_directory(project_id, storage_root) / "project.json"
    if not path.exists():
        raise FileNotFoundError(f"Project not found: {project_id}")
    return project_from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_projects(storage_root: Path | str = "storage") -> list[dict[str, Any]]:
    root = Path(storage_root) / "realism_projects"
    if not root.exists():
        return []
    projects: list[dict[str, Any]] = []
    for project_file in sorted(root.glob("*/project.json"), reverse=True):
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
            projects.append(
                {
                    "project_id": data["project_id"],
                    "character_name": data["character_name"],
                    "topic": data["topic"],
                    "status": data.get("status", "PLANNING"),
                    "created_at": data.get("created_at", ""),
                    "total_duration_seconds": round(
                        sum(float(shot.get("duration_seconds", 0)) for shot in data.get("shots", [])),
                        2,
                    ),
                }
            )
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    return projects


def default_shot_plan(character: CharacterDNA, topic: str) -> list[ShotSpec]:
    actions = [item["name"] for item in character.actions]
    locations = [item["name"] for item in character.locations]
    wardrobes = [item["name"] for item in character.wardrobe]
    emotions = character.voice.emotional_range

    def pick(items: list[str], index: int) -> str:
        return items[index % len(items)]

    if character.name == "Sofia":
        titles = [
            "Notice the mistake",
            "Explain the problem",
            "Demonstrate the correction",
            "Show the matched comparison",
            "Natural reaction and question",
        ]
        dialogues = [
            f"This is the small detail most people miss about {topic}.",
            "Watch what happens when the placement is only a few millimetres off.",
            "I am correcting one side first so you can compare the difference.",
            "Same face, same light, but a completely different result.",
            "Would you wear it this way, or should I test the opposite technique next?",
        ]
        cameras = [
            "mirror close-up, eye level, natural handheld movement",
            "medium close-up, camera beside the mirror",
            "macro detail of hand, brush and face interaction",
            "locked comparison shot with identical lighting",
            "medium reaction shot, gentle push-in",
        ]
    elif character.name == "Elena":
        titles = [
            "Enter and orient the viewer",
            "Show the main value",
            "Physically inspect one feature",
            "Reveal a limitation or hidden advantage",
            "Ask for the viewer decision",
        ]
        dialogues = [
            f"Before we discuss {topic}, notice how the entrance controls the whole layout.",
            "This is the feature that creates most of the usable value.",
            "I am checking it rather than guessing, because the dimensions matter here.",
            "The beautiful part is obvious, but this hidden detail changes the buying decision.",
            "Would you choose this property at the stated conditions?",
        ]
        cameras = [
            "wide vertical establishing shot, slow walk-in",
            "medium tracking shot through the room",
            "over-the-shoulder detail shot of the inspection",
            "close-up reaction followed by architectural reveal",
            "stable medium shot with the property behind the presenter",
        ]
    else:
        titles = [
            "Impossible event",
            "Silent emotional reaction",
            "Investigate the evidence",
            "Physical danger increases",
            "Cliffhanger choice",
        ]
        dialogues = [
            f"The message mentioned {topic}, but its timestamp says tomorrow.",
            "I knew the voice in the recording, and that was the part that frightened me.",
            "The reflection shows someone who was not in the room.",
            "The corridor light just turned on by itself.",
            "Do I open the door, or call the person who sent the message?",
        ]
        cameras = [
            "phone insert followed by close-up rack focus to the eyes",
            "tight close-up, almost still camera, audible breathing",
            "over-the-shoulder evidence inspection",
            "wide corridor shot, motivated handheld retreat",
            "close-up with doorway out of focus behind the character",
        ]

    shots: list[ShotSpec] = []
    for index, title in enumerate(titles):
        shots.append(
            ShotSpec(
                shot_number=index + 1,
                title=title,
                duration_seconds=5.0 if index < 4 else 6.0,
                dialogue=dialogues[index],
                emotion=pick(emotions, index),
                action_name=pick(actions, index),
                location_name=pick(locations, 0 if index < 3 else index),
                wardrobe_name=pick(wardrobes, 0),
                camera=cameras[index],
            )
        )
    return shots


def build_realism_manifest(project: RealismProject, character: CharacterDNA) -> dict[str, Any]:
    blockers = project.rights.hard_blockers()
    shot_packages: list[dict[str, Any]] = []
    for shot in project.shots:
        package = build_scene_direction(
            character,
            dialogue=shot.dialogue,
            emotion=shot.emotion,
            action_name=shot.action_name,
            location_name=shot.location_name,
            wardrobe_name=shot.wardrobe_name,
            camera=shot.camera,
            duration_seconds=shot.duration_seconds,
        )
        package.update(
            {
                "shot_number": shot.shot_number,
                "title": shot.title,
                "performance_source": shot.performance_source,
                "notes": shot.notes,
            }
        )
        shot_packages.append(package)

    return {
        "schema_version": 1,
        "project": asdict(project),
        "character_dna": character_to_dict(character),
        "rights_status": {
            "approved": not blockers,
            "hard_blockers": blockers,
            "ai_disclosure_required": project.rights.ai_disclosure_required,
        },
        "production_strategy": {
            "recommended_mode": "actor_performance_plus_identity_transfer",
            "reason": (
                "Real eye movement, timing, object interaction and body mechanics are preserved from "
                "a consenting performer while the fictional identity remains consistent."
            ),
            "shot_duration_rule": "Prefer 3-8 second controlled shots; regenerate failed shots individually.",
            "audio_rule": "Use one licensed voice identity plus room tone, object sounds, footsteps and breathing.",
            "editing_rule": "Use motivated cuts and preserve spatial continuity.",
        },
        "stages": [
            {"stage": 1, "name": "Performance capture", "input": "Consenting actor footage or fully synthetic motion reference", "output": "Short shot-level performance clips"},
            {"stage": 2, "name": "Identity transfer", "input": "Approved master face and reference pack", "output": "Character-consistent shot clips"},
            {"stage": 3, "name": "Voice and lip sync", "input": "Licensed voice ID or consenting actor voice", "output": "Emotion-matched dialogue with natural timing"},
            {"stage": 4, "name": "Sound design", "input": "Room tone, object interactions, footsteps and breathing", "output": "Believable acoustic environment"},
            {"stage": 5, "name": "Assembly and quality gate", "input": "Approved shots, narration and subtitles", "output": "1080x1920 master video"},
        ],
        "shots": shot_packages,
    }


def _format_srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(shots: Iterable[ShotSpec]) -> str:
    lines: list[str] = []
    cursor = 0.0
    for index, shot in enumerate(shots, start=1):
        start = cursor
        end = cursor + shot.duration_seconds
        lines.extend([str(index), f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}", shot.dialogue.strip(), ""])
        cursor = end
    return "\n".join(lines).strip() + "\n"


def save_manifest_and_subtitles(project: RealismProject, character: CharacterDNA, storage_root: Path | str = "storage") -> dict[str, Path]:
    paths = ensure_project_structure(project.project_id, storage_root)
    manifest_path = paths["manifests"] / "realism_manifest.json"
    manifest_path.write_text(json.dumps(build_realism_manifest(project, character), ensure_ascii=False, indent=2), encoding="utf-8")
    srt_path = paths["subtitles"] / "subtitles.srt"
    srt_path.write_text(generate_srt(project.shots), encoding="utf-8")
    project_path = save_project(project, storage_root)
    return {"manifest": manifest_path, "subtitles": srt_path, "project": project_path}


def export_project_package(project: RealismProject, character: CharacterDNA, storage_root: Path | str = "storage") -> Path:
    saved = save_manifest_and_subtitles(project, character, storage_root)
    paths = ensure_project_structure(project.project_id, storage_root)
    checklist = paths["manifests"] / "human_review_checklist.txt"
    checklist.write_text(
        "\n".join([
            "REALISM HUMAN REVIEW",
            "",
            "[ ] Face geometry matches approved references",
            "[ ] Eye color and hair remain stable",
            "[ ] Signature item is correct",
            "[ ] Hands and object interactions are believable",
            "[ ] Lip sync matches the chosen licensed voice",
            "[ ] Natural blinking, breathing and eye-line changes are present",
            "[ ] Lighting and room geometry remain stable",
            "[ ] Spoken facts match captions and metadata",
            "[ ] Rights and consent are documented",
            "[ ] AI disclosure is prepared when required",
        ]),
        encoding="utf-8",
    )
    archive_path = paths["exports"] / f"{project.project_id}-production-package.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [saved["manifest"], saved["subtitles"], saved["project"], checklist]:
            archive.write(path, arcname=path.relative_to(paths["root"]))
    return archive_path


def ordered_generated_shots(project_id: str, storage_root: Path | str = "storage") -> list[Path]:
    folder = ensure_project_structure(project_id, storage_root)["generated_shots"]
    return sorted(
        [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS],
        key=lambda path: path.name.lower(),
    )


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _escape_subtitle_filter_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    return value.replace(":", r"\:").replace("'", r"\'")


def render_vertical_video(
    shot_files: list[Path],
    output_path: Path,
    *,
    narration_audio: Path | None = None,
    subtitles_srt: Path | None = None,
    ffmpeg_binary: str | None = None,
) -> Path:
    if not shot_files:
        raise ValueError("At least one generated shot clip is required.")
    ffmpeg = ffmpeg_binary or find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found. Install FFmpeg and make sure it is available on PATH.")
    for shot in shot_files:
        if not shot.exists() or shot.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid shot clip: {shot}")
    if narration_audio and not narration_audio.exists():
        raise ValueError("Narration audio file does not exist.")
    if subtitles_srt and not subtitles_srt.exists():
        raise ValueError("Subtitle file does not exist.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="creator-render-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        normalized: list[Path] = []
        video_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p"
        for index, shot in enumerate(shot_files, start=1):
            normalized_path = temp_dir / f"normalized-{index:02d}.mp4"
            subprocess.run(
                [ffmpeg, "-y", "-i", str(shot), "-vf", video_filter, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(normalized_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            normalized.append(normalized_path)

        concat_file = temp_dir / "concat.txt"
        concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in normalized), encoding="utf-8")
        silent_master = temp_dir / "silent-master.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent_master)],
            check=True,
            capture_output=True,
            text=True,
        )

        final_command = [ffmpeg, "-y", "-i", str(silent_master)]
        if narration_audio:
            final_command += ["-i", str(narration_audio)]
        if subtitles_srt:
            subtitle_path = _escape_subtitle_filter_path(subtitles_srt)
            final_command += [
                "-vf",
                f"subtitles='{subtitle_path}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=90'",
            ]
        final_command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
        if narration_audio:
            final_command += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        else:
            final_command += ["-an"]
        final_command += ["-movflags", "+faststart", str(output_path)]
        subprocess.run(final_command, check=True, capture_output=True, text=True)

    return output_path


def evaluate_realism_gate(checks: dict[str, bool], rights: RightsRecord) -> dict[str, Any]:
    hard_blockers = rights.hard_blockers()
    failed = [name for name, passed in checks.items() if not passed]
    total = len(checks)
    passed_count = total - len(failed)
    score = round((passed_count / total * 100) if total else 0.0, 1)

    if hard_blockers:
        status = "BLOCKED — RIGHTS OR CONSENT"
    elif failed:
        status = "REJECT OR FIX"
    elif score == 100:
        status = "APPROVED FOR HUMAN REVIEW"
    else:
        status = "INCOMPLETE"

    return {
        "score": score,
        "passed": passed_count,
        "total": total,
        "failed_checks": failed,
        "hard_blockers": hard_blockers,
        "status": status,
    }
