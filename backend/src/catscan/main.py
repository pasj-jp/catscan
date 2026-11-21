from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.scan import router as scan_router
from .api.reports import router as reports_router
from .api.indico import router as indico_router
from .errors import CatScanError, TemplateMismatchError
from .settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    application = FastAPI(
        title="CatScan Backend API",
        description="Automated paper formatting validation service for PASJ & JACoW conferences.",
        version="1.0.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @application.exception_handler(CatScanError)
    def catscan_error_handler(request: Request, exc: CatScanError):
        content = {"error": str(exc)}
        if isinstance(exc, TemplateMismatchError):
            content.update(code="template_mismatch", selected_template=exc.selected, detected_template=exc.detected)
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )

    application.include_router(scan_router)
    application.include_router(reports_router)
    application.include_router(indico_router)

    @application.get("/api/health")
    def health_check():
        return {"status": "ok", "service": "catscan-backend"}

    return application


app = create_app()
