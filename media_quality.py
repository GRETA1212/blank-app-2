from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class MediaQualityError(RuntimeError):
    pass


def _run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise MediaQualityError(f"{command[0]} is not installed or not on PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise MediaQualityError(f"{command[0]} timed out while checking the media.") from error


def probe_media(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(source),
        ]
    )
    if result.returncode != 0:
        raise MediaQualityError(result.stderr.strip() or "ffprobe could not read the media.")
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    video = video_streams[0] if video_streams else {}
    audio = audio_streams[0] if audio_streams else {}
    duration = float((payload.get("format") or {}).get("duration") or video.get("duration") or 0)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    return {
        "path": str(source),
        "duration_seconds": round(duration, 3),
        "size_bytes": source.stat().st_size,
        "format_name": (payload.get("format") or {}).get("format_name", ""),
        "video_streams": len(video_streams),
        "audio_streams": len(audio_streams),
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 4) if height else 0.0,
        "video_codec": video.get("codec_name", ""),
        "pixel_format": video.get("pix_fmt", ""),
        "frame_rate": _frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "audio_codec": audio.get("codec_name", ""),
        "sample_rate": int(audio.get("sample_rate") or 0),
        "channels": int(audio.get("channels") or 0),
        "raw": payload,
    }


def _frame_rate(value: Any) -> float:
    text = str(value or "")
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        denominator_value = float(denominator or 1)
        return round(float(numerator or 0) / denominator_value, 3) if denominator_value else 0.0
    try:
        return round(float(text), 3)
    except ValueError:
        return 0.0


def detect_black_frames(path: str | Path, picture_black_ratio: float = 0.98) -> list[dict[str, float]]:
    result = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            f"blackdetect=d=0.25:pic_th={picture_black_ratio}",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    text = f"{result.stdout}\n{result.stderr}"
    rows: list[dict[str, float]] = []
    pattern = re.compile(r"black_start:(?P<start>[\d.]+)\s+black_end:(?P<end>[\d.]+)\s+black_duration:(?P<duration>[\d.]+)")
    for match in pattern.finditer(text):
        rows.append({key: float(value) for key, value in match.groupdict().items()})
    return rows


def detect_freezes(path: str | Path) -> list[dict[str, float]]:
    result = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "freezedetect=n=-50dB:d=1.2",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    text = f"{result.stdout}\n{result.stderr}"
    starts = [float(value) for value in re.findall(r"freeze_start:\s*([\d.]+)", text)]
    ends = [float(value) for value in re.findall(r"freeze_end:\s*([\d.]+)", text)]
    durations = [float(value) for value in re.findall(r"freeze_duration:\s*([\d.]+)", text)]
    rows: list[dict[str, float]] = []
    for index, start in enumerate(starts):
        row = {"start": start}
        if index < len(ends):
            row["end"] = ends[index]
        if index < len(durations):
            row["duration"] = durations[index]
        rows.append(row)
    return rows


def detect_silence(path: str | Path) -> list[dict[str, float]]:
    result = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-42dB:d=1.0",
            "-vn",
            "-f",
            "null",
            "-",
        ]
    )
    text = f"{result.stdout}\n{result.stderr}"
    starts = [float(value) for value in re.findall(r"silence_start:\s*([\d.]+)", text)]
    ends = [float(value) for value in re.findall(r"silence_end:\s*([\d.]+)", text)]
    durations = [float(value) for value in re.findall(r"silence_duration:\s*([\d.]+)", text)]
    rows: list[dict[str, float]] = []
    for index, start in enumerate(starts):
        row = {"start": start}
        if index < len(ends):
            row["end"] = ends[index]
        if index < len(durations):
            row["duration"] = durations[index]
        rows.append(row)
    return rows


def technical_qc(
    path: str | Path,
    *,
    expected_vertical: bool = True,
    min_width: int = 720,
    min_height: int = 1280,
    max_duration_seconds: float = 180.0,
    deep_scan: bool = True,
) -> dict[str, Any]:
    probe = probe_media(path)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str, severity: str = "BLOCK") -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "detail": detail,
                "severity": severity,
            }
        )

    add("Video stream", probe["video_streams"] > 0, f"{probe['video_streams']} video stream(s)")
    add("Audio stream", probe["audio_streams"] > 0, f"{probe['audio_streams']} audio stream(s)")
    if expected_vertical:
        add(
            "Vertical format",
            probe["height"] > probe["width"],
            f"{probe['width']}×{probe['height']}",
        )
    add(
        "Minimum resolution",
        probe["width"] >= min_width and probe["height"] >= min_height,
        f"{probe['width']}×{probe['height']} expected at least {min_width}×{min_height}",
    )
    add(
        "Duration",
        0 < probe["duration_seconds"] <= max_duration_seconds,
        f"{probe['duration_seconds']:.2f} seconds",
    )
    add(
        "Frame rate",
        probe["frame_rate"] >= 23.0,
        f"{probe['frame_rate']:.2f} fps",
        severity="WARN",
    )
    add(
        "Audio sample rate",
        probe["sample_rate"] in (44100, 48000),
        f"{probe['sample_rate']} Hz",
        severity="WARN",
    )

    black_frames: list[dict[str, float]] = []
    freezes: list[dict[str, float]] = []
    silences: list[dict[str, float]] = []
    if deep_scan and shutil.which("ffmpeg"):
        black_frames = detect_black_frames(path)
        freezes = detect_freezes(path)
        silences = detect_silence(path)
        black_total = sum(item.get("duration", 0.0) for item in black_frames)
        freeze_total = sum(item.get("duration", 0.0) for item in freezes)
        long_silence = max((item.get("duration", 0.0) for item in silences), default=0.0)
        add("Blank frames", black_total <= 0.8, f"{black_total:.2f} seconds detected", severity="WARN")
        add("Frozen frames", freeze_total <= 1.2, f"{freeze_total:.2f} seconds detected", severity="WARN")
        add("Unexpected silence", long_silence <= 2.5, f"Longest silence {long_silence:.2f} seconds", severity="WARN")

    block_failures = [item for item in checks if not item["passed"] and item["severity"] == "BLOCK"]
    warnings = [item for item in checks if not item["passed"] and item["severity"] == "WARN"]
    score = max(0.0, 100.0 - len(block_failures) * 22.0 - len(warnings) * 7.0)
    return {
        "path": str(path),
        "probe": probe,
        "checks": checks,
        "black_frames": black_frames,
        "freezes": freezes,
        "silences": silences,
        "score": round(score, 1),
        "ready": not block_failures and score >= 75,
        "blockers": [item["detail"] for item in block_failures],
        "warnings": [item["detail"] for item in warnings],
    }


def validate_thumbnail(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover
        raise MediaQualityError("Pillow is required to validate thumbnails.") from error
    with Image.open(source) as image:
        width, height = image.size
        mode = image.mode
        image_format = image.format or source.suffix.removeprefix(".").upper()
    ratio = width / height if height else 0
    checks = [
        {
            "name": "Recommended dimensions",
            "passed": width >= 1280 and height >= 720,
            "detail": f"{width}×{height}",
        },
        {
            "name": "16:9 aspect",
            "passed": abs(ratio - 16 / 9) <= 0.05,
            "detail": f"{ratio:.3f}",
        },
        {
            "name": "File size",
            "passed": source.stat().st_size <= 2 * 1024 * 1024,
            "detail": f"{source.stat().st_size / 1024:.1f} KB",
        },
        {
            "name": "Supported format",
            "passed": image_format.upper() in {"JPG", "JPEG", "PNG", "WEBP"},
            "detail": image_format,
        },
    ]
    return {
        "path": str(source),
        "width": width,
        "height": height,
        "mode": mode,
        "format": image_format,
        "checks": checks,
        "ready": all(item["passed"] for item in checks),
    }
