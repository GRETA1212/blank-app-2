from .audio_enhancements import bootstrap_voices, router as audio_router
from .main import app

app.include_router(audio_router)


@app.on_event("startup")
def install_default_neural_voices() -> None:
    bootstrap_voices()


__all__ = ["app"]
