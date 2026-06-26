from pathlib import Path
import wave

from fastapi import HTTPException

from .main import run


def synthesize_with_runtime(text: str, output: Path, language_code: str, voice_id: str | None, speed: float, audio_module) -> tuple[str, str]:
    selected = voice_id or audio_module.DEFAULT_VOICE_BY_LANGUAGE.get(language_code, "mk-espeak")
    voice_meta = audio_module.VOICE_CATALOG.get(selected)
    if voice_meta and voice_meta["engine"] == "piper":
        try:
            from piper import SynthesisConfig

            voice = audio_module._piper_voice(selected)
            config = SynthesisConfig(length_scale=1.0 / speed)
            with wave.open(str(output), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file, syn_config=config)
            return f"piper:{selected}", selected
        except Exception as exc:
            if voice_id:
                raise HTTPException(status_code=500, detail=f"Piper synthesis failed: {exc}") from exc
            print(f"Piper fallback warning: {exc}", flush=True)

    espeak_voice = audio_module.ESPEAK_BY_LANGUAGE.get(language_code, "en-us")
    text_path = output.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    rate = max(90, min(260, round(155 * speed)))
    run(["espeak-ng", "-v", espeak_voice, "-s", str(rate), "-f", str(text_path), "-w", str(output)], timeout=300)
    return f"espeak-ng:{espeak_voice}", f"{language_code}-espeak"
