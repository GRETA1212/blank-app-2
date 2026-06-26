from . import audio_enhancements
from .main import app, render_segment as base_render_segment, validated_asset
from .tts_runtime import synthesize_with_runtime


def synthesize_runtime(text, output, language_code, voice_id, speed):
    return synthesize_with_runtime(text, output, language_code, voice_id, speed, audio_enhancements)


def render_with_asset(scene, _asset, output, duration, width, height, title, job_dir):
    return base_render_segment(scene, validated_asset(scene), output, duration, width, height, title, job_dir)


audio_enhancements.synthesize_enhanced = synthesize_runtime
audio_enhancements.render_segment = render_with_asset
app.include_router(audio_enhancements.router)


@app.on_event("startup")
def install_default_neural_voices() -> None:
    audio_enhancements.bootstrap_voices()


__all__ = ["app"]
