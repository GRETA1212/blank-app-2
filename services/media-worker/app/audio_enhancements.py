import json
import os
import re
import subprocess
import unicodedata
import wave
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .main import (
    OUTPUT_ROOT,
    VOICE_ROOT,
    Scene,
    dimensions,
    media_duration,
    normalized_durations,
    render_segment,
    run,
)

router = APIRouter(tags=["audio"])
WHISPER_ROOT = Path(os.getenv("WHISPER_ROOT", "/models/whisper")).resolve()
WHISPER_ROOT.mkdir(parents=True, exist_ok=True)
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
VERIFY_THRESHOLD = float(os.getenv("SUBTITLE_VERIFY_THRESHOLD", "0.82"))
PIPER_AUTO_DOWNLOAD = os.getenv("PIPER_AUTO_DOWNLOAD", "true").lower() in {"1", "true", "yes"}
AUTO_VOICES = [item.strip() for item in os.getenv(
    "PIPER_AUTO_VOICES",
    "en_US-lessac-medium,it_IT-paola-medium,sq_AL-edon-medium",
).split(",") if item.strip()]

VOICE_CATALOG: dict[str, dict[str, Any]] = {
    "en_US-lessac-medium": {
        "id": "en_US-lessac-medium",
        "display_name": "English — Lessac (neural)",
        "language_code": "en",
        "engine": "piper",
        "natural": True,
        "recommended": True,
        "model_source": "rhasspy/piper-voices",
        "license_review_required": True,
    },
    "it_IT-paola-medium": {
        "id": "it_IT-paola-medium",
        "display_name": "Italian — Paola (neural)",
        "language_code": "it",
        "engine": "piper",
        "natural": True,
        "recommended": True,
        "model_source": "rhasspy/piper-voices",
        "license_review_required": True,
    },
    "sq_AL-edon-medium": {
        "id": "sq_AL-edon-medium",
        "display_name": "Albanian — Edon (neural)",
        "language_code": "sq",
        "engine": "piper",
        "natural": True,
        "recommended": True,
        "model_source": "rhasspy/piper-voices",
        "license_review_required": True,
    },
    "mk-espeak": {
        "id": "mk-espeak",
        "display_name": "Macedonian — eSpeak NG fallback",
        "language_code": "mk",
        "engine": "espeak-ng",
        "natural": False,
        "recommended": True,
        "model_source": "system",
        "license_review_required": False,
    },
}

ESPEAK_BY_LANGUAGE = {"en": "en-us", "it": "it", "sq": "sq", "mk": "mk"}
DEFAULT_VOICE_BY_LANGUAGE = {
    "en": "en_US-lessac-medium",
    "it": "it_IT-paola-medium",
    "sq": "sq_AL-edon-medium",
    "mk": "mk-espeak",
}
_PIPER_CACHE: dict[str, Any] = {}
_WHISPER_MODEL: Any | None = None


class EnhancedVoicePreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language_code: Literal["en", "it", "sq", "mk"] = "en"
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.65, le=1.5)


class EnhancedRenderRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    narration: str = Field(min_length=20, max_length=100000)
    scenes: list[Scene] = Field(default_factory=list)
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    language_code: Literal["en", "it", "sq", "mk"] = "en"
    voice_id: str | None = None
    voice_speed: float = Field(default=1.0, ge=0.65, le=1.5)
    burn_subtitles: bool = True
    verify_subtitles: bool = True


def voice_model_path(voice_id: str) -> Path:
    return VOICE_ROOT / f"{voice_id}.onnx"


def voice_installed(voice_id: str) -> bool:
    if VOICE_CATALOG.get(voice_id, {}).get("engine") == "espeak-ng":
        return True
    model = voice_model_path(voice_id)
    return model.is_file() and model.with_suffix(".onnx.json").is_file()


def install_voice(voice_id: str) -> dict[str, Any]:
    voice = VOICE_CATALOG.get(voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice is not in the approved local catalogue")
    if voice["engine"] != "piper":
        return {**voice, "installed": True}
    if voice_installed(voice_id):
        return {**voice, "installed": True}
    try:
        subprocess.run(
            ["python", "-m", "piper.download_voices", "--data-dir", str(VOICE_ROOT), voice_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise HTTPException(status_code=502, detail=f"Voice download failed: {detail[-1200:]}") from exc
    if not voice_installed(voice_id):
        raise HTTPException(status_code=502, detail="Voice download finished without the required model files")
    metadata = {
        "voice_id": voice_id,
        "source": voice["model_source"],
        "license_review_required": voice["license_review_required"],
    }
    (VOICE_ROOT / f"{voice_id}.source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {**voice, "installed": True}


def bootstrap_voices() -> None:
    if not PIPER_AUTO_DOWNLOAD:
        return
    for voice_id in AUTO_VOICES:
        try:
            install_voice(voice_id)
        except Exception as exc:
            print(f"Voice bootstrap warning for {voice_id}: {exc}", flush=True)


def _piper_voice(voice_id: str) -> Any:
    if voice_id not in _PIPER_CACHE:
        install_voice(voice_id)
        from piper import PiperVoice

        _PIPER_CACHE[voice_id] = PiperVoice.load(str(voice_model_path(voice_id)))
    return _PIPER_CACHE[voice_id]


def synthesize_enhanced(
    text: str,
    output: Path,
    language_code: str,
    voice_id: str | None,
    speed: float,
) -> tuple[str, str]:
    selected = voice_id or DEFAULT_VOICE_BY_LANGUAGE.get(language_code, "mk-espeak")
    voice = VOICE_CATALOG.get(selected)
    if voice and voice["engine"] == "piper":
        try:
            piper_voice = _piper_voice(selected)
            with wave.open(str(output), "wb") as wav_file:
                piper_voice.synthesize_wav(text, wav_file, length_scale=1.0 / speed)
            return f"piper:{selected}", selected
        except Exception as exc:
            if voice_id:
                raise HTTPException(status_code=500, detail=f"Piper synthesis failed: {exc}") from exc
            print(f"Piper fallback warning: {exc}", flush=True)

    espeak_voice = ESPEAK_BY_LANGUAGE.get(language_code, "en-us")
    text_path = output.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    rate = max(90, min(260, round(155 * speed)))
    run(["espeak-ng", "-v", espeak_voice, "-s", str(rate), "-f", str(text_path), "-w", str(output)], timeout=300)
    return f"espeak-ng:{espeak_voice}", f"{language_code}-espeak"


def _whisper() -> Any:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        _WHISPER_MODEL = WhisperModel(
            WHISPER_MODEL_NAME,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            download_root=str(WHISPER_ROOT),
        )
    return _WHISPER_MODEL


def srt_timestamp(value: float) -> str:
    milliseconds = max(0, int(round(value * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def normalized_words(text: str) -> list[str]:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = re.sub(r"[^\w\s'-]", " ", value, flags=re.UNICODE)
    return [word for word in value.split() if word]


def verify_audio(
    audio_path: Path,
    intended_text: str,
    language_code: str,
    srt_path: Path,
    transcript_path: Path,
) -> dict[str, Any]:
    model = _whisper()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language_code,
        beam_size=5,
        vad_filter=True,
        word_timestamps=False,
    )
    segments = list(segments_iter)
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    transcript_path.write_text(transcript, encoding="utf-8")
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{srt_timestamp(segment.start)} --> {srt_timestamp(segment.end)}\n{segment.text.strip()}\n"
        )
    srt_path.write_text("\n".join(blocks), encoding="utf-8")

    intended = normalized_words(intended_text)
    actual = normalized_words(transcript)
    similarity = SequenceMatcher(None, intended, actual).ratio() if intended or actual else 1.0
    missing = list((Counter(intended) - Counter(actual)).elements())[:30]
    unexpected = list((Counter(actual) - Counter(intended)).elements())[:30]
    passed = similarity >= VERIFY_THRESHOLD
    return {
        "passed": passed,
        "similarity": round(similarity, 4),
        "threshold": VERIFY_THRESHOLD,
        "detected_language": getattr(info, "language", language_code),
        "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
        "segment_count": len(segments),
        "missing_words_sample": missing,
        "unexpected_words_sample": unexpected,
        "warning": "" if passed else "The generated audio differs materially from the intended narration. Review pronunciation and transcript before publishing.",
    }


@router.get("/audio/voices")
def enhanced_voices(language_code: str | None = None) -> dict[str, Any]:
    voices = []
    for voice in VOICE_CATALOG.values():
        if language_code and voice["language_code"] != language_code:
            continue
        voices.append({**voice, "installed": voice_installed(voice["id"])})
    return {
        "voices": voices,
        "defaults": DEFAULT_VOICE_BY_LANGUAGE,
        "notice": "Piper voice models have separate model cards. Review each model licence before commercial distribution.",
    }


@router.post("/audio/voices/{voice_id}/install")
def install_catalogue_voice(voice_id: str) -> dict[str, Any]:
    return install_voice(voice_id)


@router.post("/audio/voice-preview")
def enhanced_voice_preview(request: EnhancedVoicePreviewRequest) -> dict[str, Any]:
    preview_id = uuid4().hex
    directory = OUTPUT_ROOT / "previews" / preview_id
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "voice.wav"
    engine, selected = synthesize_enhanced(
        request.text,
        output,
        request.language_code,
        request.voice_id,
        request.speed,
    )
    return {
        "audio_path": f"previews/{preview_id}/voice.wav",
        "voice_engine": engine,
        "voice_id": selected,
        "language_code": request.language_code,
    }


@router.post("/render-v2")
def render_enhanced(request: EnhancedRenderRequest) -> dict[str, Any]:
    job_id = uuid4().hex
    job_dir = (OUTPUT_ROOT / job_id).resolve()
    job_dir.mkdir(parents=True, exist_ok=False)
    width, height = dimensions(request.aspect_ratio)
    narration_wav = job_dir / "narration.wav"
    subtitles = job_dir / "subtitles.srt"
    transcript = job_dir / "transcript.txt"
    output_video = job_dir / "draft.mp4"

    voice_engine, selected_voice = synthesize_enhanced(
        request.narration,
        narration_wav,
        request.language_code,
        request.voice_id,
        request.voice_speed,
    )
    duration = media_duration(narration_wav)
    scenes = request.scenes or [
        Scene(
            scene_number=1,
            duration_seconds=max(round(duration), 1),
            purpose=request.title,
            onscreen_text=request.title,
        )
    ]
    durations = normalized_durations(scenes, duration)
    segment_paths: list[Path] = []
    for index, (scene, scene_duration) in enumerate(zip(scenes, durations, strict=True), start=1):
        segment = job_dir / f"segment_{index:03d}.mp4"
        render_segment(scene, None, segment, scene_duration, width, height, request.title, job_dir)
        segment_paths.append(segment)

    concat_file = job_dir / "segments.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in segment_paths), encoding="utf-8")
    silent_video = job_dir / "video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent_video)])

    verification: dict[str, Any]
    if request.verify_subtitles:
        try:
            verification = verify_audio(
                narration_wav,
                request.narration,
                request.language_code,
                subtitles,
                transcript,
            )
        except Exception as exc:
            from .main import make_subtitles

            make_subtitles(request.narration, duration, subtitles)
            transcript.write_text("", encoding="utf-8")
            verification = {
                "passed": False,
                "similarity": None,
                "warning": f"Whisper verification failed; estimated subtitles were used: {exc}",
            }
    else:
        from .main import make_subtitles

        make_subtitles(request.narration, duration, subtitles)
        transcript.write_text("", encoding="utf-8")
        verification = {
            "passed": False,
            "similarity": None,
            "warning": "Whisper verification was disabled; subtitles are estimated from script timing.",
        }

    command = ["ffmpeg", "-y", "-i", str(silent_video), "-i", str(narration_wav)]
    if request.burn_subtitles:
        escaped = str(subtitles).replace("'", "\\'").replace(":", "\\:")
        command.extend(["-vf", f"subtitles='{escaped}':force_style='FontName=DejaVu Sans,FontSize=18,Outline=2,Shadow=1,MarginV=40'"])
    command.extend([
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(output_video),
    ])
    run(command)

    return {
        "job_id": job_id,
        "project_id": request.project_id,
        "duration_seconds": round(duration, 2),
        "video_path": f"{job_id}/draft.mp4",
        "subtitle_path": f"{job_id}/subtitles.srt",
        "transcript_path": f"{job_id}/transcript.txt",
        "voice_engine": voice_engine,
        "voice_id": selected_voice,
        "language_code": request.language_code,
        "subtitle_verification": verification,
        "aspect_ratio": request.aspect_ratio,
        "disclaimer": "Generated local draft. Human factual, rights, visual, audio, subtitle, translation, and disclosure review is required.",
    }
