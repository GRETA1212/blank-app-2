import math
import os
import re
import subprocess
from pathlib import Path
from textwrap import wrap
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "/output")).resolve()
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
VOICE = os.getenv("ESPEAK_VOICE", "en-us")
SPEAK_RATE = os.getenv("ESPEAK_RATE", "155")

app = FastAPI(title="Studio Media Worker", version="0.1.0")
app.mount("/files", StaticFiles(directory=str(OUTPUT_ROOT)), name="files")


class Scene(BaseModel):
    scene_number: int
    duration_seconds: int = Field(default=10, ge=1, le=600)
    purpose: str = ""
    visual_direction: str = ""
    onscreen_text: str = ""
    voice_segment: str = ""
    asset_notes: str = ""


class RenderRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    narration: str = Field(min_length=20, max_length=100000)
    scenes: list[Scene] = Field(default_factory=list)
    width: int = Field(default=1280, ge=640, le=3840)
    height: int = Field(default=720, ge=360, le=2160)


def run(command: list[str], timeout: int = 600) -> None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise HTTPException(status_code=500, detail=f"Media command failed: {detail[-1200:]}") from exc
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Media command failed")


def audio_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return max(float(result.stdout.strip()), 1.0)
    except (subprocess.SubprocessError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Could not determine narration duration") from exc


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size=size)


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    width_chars: int,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: int = 10,
) -> int:
    y = xy[1]
    for paragraph in text.splitlines() or [""]:
        lines = wrap(paragraph.strip(), width=width_chars) or [""]
        for line in lines:
            draw.text((xy[0], y), line, font=text_font, fill=fill)
            box = draw.textbbox((xy[0], y), line or " ", font=text_font)
            y += box[3] - box[1] + spacing
        y += spacing
    return y


def create_scene_image(path: Path, scene: Scene, title: str, width: int, height: int) -> None:
    image = Image.new("RGB", (width, height), (17, 16, 14))
    draw = ImageDraw.Draw(image)
    amber = (214, 168, 75)
    parchment = (238, 229, 209)
    muted = (155, 149, 141)
    panel = (29, 26, 22)

    draw.rectangle((0, 0, width, 10), fill=amber)
    draw.rectangle((48, 55, width - 48, height - 55), fill=panel, outline=(70, 61, 49), width=2)
    draw.text((78, 80), f"SCENE {scene.scene_number:02d}", font=font(24), fill=amber)
    draw.text((width - 260, 80), "STUDIO DRAFT", font=font(18), fill=muted)
    draw_wrapped(draw, title, (78, 135), 45, font(42), parchment, 12)

    on_screen = scene.onscreen_text.strip() or scene.purpose.strip() or "Visual direction"
    y = draw_wrapped(draw, on_screen, (78, 270), 48, font(34), parchment, 12)
    if scene.visual_direction.strip():
        draw_wrapped(draw, scene.visual_direction, (78, min(y + 20, height - 190)), 78, font(22), muted, 8)

    draw.line((78, height - 105, width - 78, height - 105), fill=(65, 57, 47), width=1)
    draw.text((78, height - 82), "LOCAL AI DRAFT · HUMAN REVIEW REQUIRED", font=font(18), fill=muted)
    image.save(path, format="PNG", optimize=True)


def seconds_to_srt(value: float) -> str:
    milliseconds = max(0, int(round(value * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def make_subtitles(narration: str, duration: float, path: Path) -> None:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", narration.strip()) if item.strip()]
    if not sentences:
        sentences = [narration.strip()]
    weights = [max(len(sentence.split()), 1) for sentence in sentences]
    total_weight = sum(weights)
    cursor = 0.0
    blocks: list[str] = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights, strict=True), start=1):
        segment = duration * weight / total_weight
        end = duration if index == len(sentences) else min(duration, cursor + segment)
        blocks.append(
            f"{index}\n{seconds_to_srt(cursor)} --> {seconds_to_srt(end)}\n{sentence}\n"
        )
        cursor = end
    path.write_text("\n".join(blocks), encoding="utf-8")


def normalized_durations(scenes: list[Scene], duration: float) -> list[float]:
    weights = [max(scene.duration_seconds, 1) for scene in scenes]
    total = sum(weights)
    values = [max(duration * weight / total, 0.5) for weight in weights]
    correction = duration - sum(values)
    values[-1] = max(values[-1] + correction, 0.5)
    return values


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ffmpeg": Path("/usr/bin/ffmpeg").exists(),
        "espeak": Path("/usr/bin/espeak-ng").exists(),
        "output_root": str(OUTPUT_ROOT),
    }


@app.post("/render")
def render(request: RenderRequest) -> dict[str, Any]:
    job_id = uuid4().hex
    job_dir = (OUTPUT_ROOT / job_id).resolve()
    if OUTPUT_ROOT not in job_dir.parents:
        raise HTTPException(status_code=400, detail="Invalid output path")
    job_dir.mkdir(parents=True, exist_ok=False)

    narration_txt = job_dir / "narration.txt"
    narration_wav = job_dir / "narration.wav"
    subtitles = job_dir / "subtitles.srt"
    output_video = job_dir / "draft.mp4"
    narration_txt.write_text(request.narration, encoding="utf-8")

    run([
        "espeak-ng",
        "-v",
        VOICE,
        "-s",
        SPEAK_RATE,
        "-f",
        str(narration_txt),
        "-w",
        str(narration_wav),
    ], timeout=180)
    duration = audio_duration(narration_wav)

    scenes = request.scenes or [
        Scene(
            scene_number=1,
            duration_seconds=max(math.ceil(duration), 1),
            purpose=request.title,
            onscreen_text=request.title,
            visual_direction="Replace this generated title card with original footage or a verified asset before publishing.",
        )
    ]
    durations = normalized_durations(scenes, duration)
    concat_lines: list[str] = []
    for index, (scene, scene_duration) in enumerate(zip(scenes, durations, strict=True), start=1):
        image_path = job_dir / f"scene_{index:03d}.png"
        create_scene_image(image_path, scene, request.title, request.width, request.height)
        concat_lines.append(f"file '{image_path.as_posix()}'")
        concat_lines.append(f"duration {scene_duration:.3f}")
    last_path = job_dir / f"scene_{len(scenes):03d}.png"
    concat_lines.append(f"file '{last_path.as_posix()}'")
    concat_file = job_dir / "scenes.txt"
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")
    make_subtitles(request.narration, duration, subtitles)

    run([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-i",
        str(narration_wav),
        "-c:v",
        "libx264",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_video),
    ])

    relative_video = f"{job_id}/draft.mp4"
    relative_subtitles = f"{job_id}/subtitles.srt"
    return {
        "job_id": job_id,
        "project_id": request.project_id,
        "duration_seconds": round(duration, 2),
        "video_path": relative_video,
        "subtitle_path": relative_subtitles,
        "voice_engine": "espeak-ng",
        "disclaimer": "Generated local draft only. Replace placeholder visuals and complete human review before publishing.",
    }
