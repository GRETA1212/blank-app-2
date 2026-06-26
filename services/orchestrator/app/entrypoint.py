from fastapi.staticfiles import StaticFiles

from .assets import ASSET_ROOT, router as assets_router
from .localization import router as localization_router
from .main import app
from .production import router as production_router
from .reviews import router as reviews_router
from .youtube import router as youtube_router

app.include_router(production_router)
app.include_router(assets_router)
app.include_router(reviews_router)
app.include_router(youtube_router)
app.include_router(localization_router)
app.mount("/assets/files", StaticFiles(directory=str(ASSET_ROOT)), name="assets")

__all__ = ["app"]
