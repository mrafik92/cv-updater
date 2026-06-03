from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.requests import Request

from .config import get_settings
from .logging_setup import configure_logging
from .middleware import RequestIDMiddleware
from .routes.diff import router as diff_router
from .routes.generate import router as generate_router
from .routes.history import router as history_router
from .routes.pdf import router as pdf_router
from .routes.resumes import router as resumes_router
from .services.pdf import shutdown_pdf, startup_pdf

try:
    configure_logging(get_settings().log_level)
except Exception:
    configure_logging("INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_pdf()
    yield
    await shutdown_pdf()


app = FastAPI(middleware=[Middleware(RequestIDMiddleware)], lifespan=lifespan)

app.include_router(generate_router)
app.include_router(pdf_router)
app.include_router(resumes_router)
app.include_router(history_router)
app.include_router(diff_router)
app.mount("/static", StaticFiles(directory="cv_tailor/static"), name="static")
templates = Jinja2Templates(directory="cv_tailor/templates")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)



