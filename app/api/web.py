from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

_APP_DIR = Path(__file__).resolve().parent.parent
_TEMPLATES_DIR = _APP_DIR / "templates"

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )
