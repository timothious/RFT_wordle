"""FastAPI entrypoint for the RFT Wordle backend."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.routes_game import router as games_router
from backend.app.api.routes_suggest import router as suggest_router
from backend.app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="RFT Wordle API",
        version="0.2.0",
        description="Backend for RFT Wordle: game play, solver/base/rft suggestions, offline GRPO training.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = detail
        else:
            payload = {"code": "http_error", "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "invalid_guess", "message": "Invalid request body"},
        )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "rft-wordle-api",
            "default_policy": settings.model_policy,
            "enable_lm": settings.enable_lm,
            "model_id": settings.model_id if settings.enable_lm else None,
        }

    app.include_router(games_router)
    app.include_router(suggest_router)
    return app


app = create_app()
