import math
import os
import re
import subprocess
import wave
from pathlib import Path
from textwrap import wrap
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "/output")).resolve()
VOICE_ROOT = Path(os.getenv("VOICE_ROOT", "/voices")).resolve()
ASSET_ROOT = Path(os.getenv("ASSET_ROOT", "/studio-assets")).resolve()
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
VOICE_ROOT.mkdir(parents=True, exist_ok=True)
ASSET_ROOT.mkdir(parents=True, exist_ok=True)
FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
ESPEAK_VOICE = os.getenv("ESPEAK_VOICE", "en-us")
ESPEAK_RATE = os.getenv("ESPEAK_RATE", "155")
PIPER_DEFAULT_VOICE = os.getenv("PIPER_DEFAULT_VOICE", "")

app = FastAPI(title="Studio Media Worker", version="0.2.0")
app.mount("/files", StaticFiles(directory=str(OUTPUT_ROOT)), name="files")


class Scene(BaseModel):
    scene_number: int
    duration_seconds: int = Field(default=10, ge=1, le=600)
    purpose: str = ""
    visual_direction: str = ""
    onscreen_text: str = ""
    voice_segment: str = ""
    asset_notes: str = ""
    asset_path: str | None = None
    asset_media_type: Literal["IMAGE", "VIDEO"] | None = None
    fit: Literal["cover", "contain"] = "cover"
    motion: Literal["none", "slow_zoom"] = "slow_zoom"


class RenderRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    narration: str = Field(min_length=20, max_length=100000)
    scenes: list[Scene] = Field(default_factory=list)
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    voice_id: str | None = None
    burn_subtitles: bool = True


class VoicePreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voice_id: str | None = None


class ShortsRequest(BaseModel):
    source_relative_path: str
    count: int = Field(default=3, ge=1, le=5)
    duration_seconds: int = Field(default=45, ge=15, le=60)


def run(command: list[str], timeout: int = 900) -> None:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise HTTPException(status_code=500, detail=f"Media command failed: {detail[-1400:]}") from exc


def media_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return max(float(result.stdout.strip()), 1.0)
    except (subprocess.SubprocessError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Could not determine media duration") from exc


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size=size)


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width_chars: int, text_font: ImageFont.FreeTypeFont, fill: tuple[int, int, int], spacing: int = 10) -> int:
    y = xy[1]
    for paragraph in text.splitlines() or [""]:
        for line in wrap(paragraph.strip(), width=width_chars) or [""]:
            draw.text((xy[0], y), line, font=text_font, fill=fill)
            box = draw.textbbox((xy[0], y), line or " ", font=text_font)
            y += box[3] - box[1] + spacing
        y += spacing
    return y


def create_scene_image(path: Path, scene: Scene, title: str, width: int, height: int) -> None:
    image = Image.new("RGB", (width, height), (17, 16, 14))
    draw = ImageDraw.Draw(image)
    amber, parchment, muted, panel = (214, 168, 75), (238, 229, 209), (155, 149, 141), (29, 26, 22)
    margin = max(34, int(width * 0.045))
    draw.rectangle((0, 0, width, max(8, height // 90)), fill=amber)
    draw.rectangle((margin, margin, width - margin, height - margin), fill=panel, outline=(70, 61, 49), width=2)
    draw.text((margin + 28, margin + 25), f"SCENE {scene.scene_number:02d}", font=font(max(18, width // 55)), fill=amber)
    title_y = margin + max(85, height // 8)
    y = draw_wrapped(draw, title, (margin + 28, title_y), 36 if height > width else 52, font(max(30, width // 30)), parchment, 10)
    on_screen = scene.onscreen_text.strip() or scene.purpose.strip() or "Add an original licensed visual"
    draw_wrapped(draw, on_screen, (margin + 28, min(y + 35, height - 230)), 38 if height > width else 60, font(max(24, width // 42)), parchment, 9)
    draw.text((margin + 28, height - margin - 48), "DRAFT · HUMAN REVIEW REQUIRED", font=font(max(16, width // 70)), fill=muted)
    image.save(path, format="PNG", optimize=True)


def seconds_to_srt(value: float) -> str:
    milliseconds = max(0, int(round(value * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def make_subtitles(narration: str, duration: float, path: Path) -> None:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", narration.strip()) if item.strip()] or [narration.strip()]
    weights = [max(len(sentence.split()), 1) for sentence in sentences]
    total_weight = sum(weights)
    cursor = 0.0
    blocks: list[str] = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights, strict=True), start=1):
        end = duration if index == len(sentences) else min(duration, cursor + duration * weight / total_weight)
        blocks.append(f"{index}\n{seconds_to_srt(cursor)} --> {seconds_to_srt(end)}\n{sentence}\n")
        cursor = end
    path.write_text("\n".join(blocks), encoding="utf-8")


def normalized_durations(scenes: list[Scene], duration: float) -> list[float]:
    weights = [max(scene.duration_seconds, 1) for scene in scenes]
    total = sum(weights)
    values = [max(duration * weight / total, 0.5) for weight in weights]
    values[-1] = max(values[-1] + duration - sum(values), 0.5)
    return values


def available_piper_voices() -> list[str]:
    return sorted(path.stem for path in VOICE_ROOT.glob("*.onnx"))


def voice_model(voice_id: str | None) -> Path | None:
    selected = voice_id or PIPER_DEFAULT_VOICE
    if not selected:
        return None
    candidate = (VOICE_ROOT / f"{selected}.onnx").resolve()
    if VOICE_ROOT not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def synthesize(text: str, output: Path, voice_id: str | None) -> str:
    model = voice_model(voice_id)
    if model is not None:
        try:
            from piper import PiperVoice

            voice = PiperVoice.load(str(model))
            with wave.open(str(output), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
            return f"piper:{model.stem}"
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Piper voice synthesis failed: {exc}") from exc

    text_path = output.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    run(["espeak-ng", "-v", ESPEAK_VOICE, "-s", ESPEAK_RATE, "-f", str(text_path), "-w", str(output)], timeout=240)
    return f"espeak-ng:{ESPEAK_VOICE}"


def dimensions(aspect_ratio: str) -> tuple[int, int]:
    return (1080, 1920) if aspect_ratio == "9:16" else (1280, 720)


def validated_asset(scene: Scene) -> Path | None:
    if not scene.asset_path:
        return None
    path = Path(scene.asset_path).resolve()
    if ASSET_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=422, detail=f"Scene {scene.scene_number} asset is unavailable")
    return path


def scale_filter(width: int, height: int, fit: str) -> str:
    if fit == "contain":
        return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"


def render_segment(scene: Scene, asset: Path | None, output: Path, duration: float, width: int, height: int, title: str, job_dir: Path) -> None:
    source = asset
    source_type = scene.asset_media_type
    if source is None:
        source = job_dir / f"placeholder_{scene.scene_number:03d}.png"
        create_scene_image(source, scene, title, width, height)
        source_type = "IMAGE"

    vf = scale_filter(width, height, scene.fit)
    if source_type == "IMAGE":
        if scene.motion == "slow_zoom":
            vf = f"{vf},zoompan=z='min(zoom+0.0006,1.08)':d=1:s={width}x{height}:fps=30"
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(source), "-t", f"{duration:.3f}", "-vf", vf, "-r", "30", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)])
    else:
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source), "-t", f"{duration:.3f}", "-vf", vf, "-r", "30", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)])


def safe_output(relative_path: str) -> Path:
    path = (OUTPUT_ROOT / relative_path).resolve()
    if OUTPUT_ROOT not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Source media is unavailable")
    return path


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ffmpeg": Path("/usr/bin/ffmpeg").exists(),
        "espeak": Path("/usr/bin/espeak-ng").exists(),
        "piper_voices": available_piper_voices(),
        "output_root": str(OUTPUT_ROOT),
    }


@app.get("/voices")
def voices() -> dict[str, Any]:
    piper = available_piper_voices()
    return {
        "voices": [{"id": voice, "engine": "piper", "natural": True} for voice in piper] + [{"id": ESPEAK_VOICE, "engine": "espeak-ng", "natural": False}],
        "default": PIPER_DEFAULT_VOICE if PIPER_DEFAULT_VOICE in piper else ESPEAK_VOICE,
    }


@app.post("/voice-preview")
def voice_preview(request: VoicePreviewRequest) -> dict[str, Any]:
    preview_id = uuid4().hex
    directory = OUTPUT_ROOT / "previews" / preview_id
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "voice.wav"
    engine = synthesize(request.text, output, request.voice_id)
    return {"audio_path": f"previews/{preview_id}/voice.wav", "voice_engine": engine}


@app.post("/render")
def render(request: RenderRequest) -> dict[str, Any]:
    job_id = uuid4().hex
    job_dir = (OUTPUT_ROOT / job_id).resolve()
    job_dir.mkdir(parents=True, exist_ok=False)
    width, height = dimensions(request.aspect_ratio)
    narration_wav = job_dir / "narration.wav"
    subtitles = job_dir / "subtitles.srt"
    output_video = job_dir / "draft.mp4"
    voice_engine = synthesize(request.narration, narration_wav, request.voice_id)
    duration = media_duration(narration_wav)

    scenes = request.scenes or [Scene(scene_number=1, duration_seconds=max(math.ceil(duration), 1), purpose=request.title, onscreen_text=request.title)]
    durations = normalized_durations(scenes, duration)
    segment_paths: list[Path] = []
    for index, (scene, scene_duration) in enumerate(zip(scenes, durations, strict=True), start=1):
        segment = job_dir / f"segment_{index:03d}.mp4"
        render_segment(scene, validated_asset(scene), segment, scene_duration, width, height, request.title, job_dir)
        segment_paths.append(segment)

    concat_file = job_dir / "segments.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in segment_paths), encoding="utf-8")
    silent_video = job_dir / "video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent_video)])
    make_subtitles(request.narration, duration, subtitles)

    command = ["ffmpeg", "-y", "-i", str(silent_video), "-i", str(narration_wav)]
    if request.burn_subtitles:
        escaped = str(subtitles).replace("'", "\\'").replace(":", "\\:")
        command.extend(["-vf", f"subtitles='{escaped}':force_style='FontName=DejaVu Sans,FontSize=18,Outline=2,Shadow=1,MarginV=40'"])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(output_video)])
    run(command)

    return {
        "job_id": job_id,
        "project_id": request.project_id,
        "duration_seconds": round(duration, 2),
        "video_path": f"{job_id}/draft.mp4",
        "subtitle_path": f"{job_id}/subtitles.srt",
        "voice_engine": voice_engine,
        "aspect_ratio": request.aspect_ratio,
        "disclaimer": "Generated local draft. Human factual, rights, visual, audio, subtitle, and disclosure review is required.",
    }


@app.post("/shorts")
def create_shorts(request: ShortsRequest) -> dict[str, Any]:
    source = safe_output(request.source_relative_path)
    total = media_duration(source)
    clip_duration = min(float(request.duration_seconds), total)
    directory_id = uuid4().hex
    directory = OUTPUT_ROOT / "derivatives" / directory_id
    directory.mkdir(parents=True, exist_ok=False)
    results: list[str] = []
    travel = max(total - clip_duration, 0.0)
    for index in range(request.count):
        start = 0.0 if request.count == 1 else travel * index / (request.count - 1)
        output = directory / f"short-{index + 1}.mp4"
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{clip_duration:.3f}", "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output)])
        results.append(f"derivatives/{directory_id}/{output.name}")
    return {"outputs": results, "count": len(results), "duration_seconds": round(clip_duration, 2), "aspect_ratio": "9:16"}
