from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.benchmark import router as benchmark_router
from app.api.sources import router as sources_router
from app.api.web import router as web_router
from app.core.config import settings

_APP_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _APP_DIR / "static"

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


app.include_router(web_router)
app.include_router(benchmark_router)
app.include_router(sources_router)
