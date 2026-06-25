from .main import app
from .production import router as production_router

app.include_router(production_router)

__all__ = ["app"]
