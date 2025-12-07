import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import get_settings
from app.auth import router as auth_router
from app.api.routers import admin  # keep admin router for now
from app.conference import router as conference_router
from app.kalamela.routers import public as kalamela_public, official as kalamela_official, admin as kalamela_admin


settings = get_settings()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(conference_router.router, prefix="/conference", tags=["conference"])
app.include_router(kalamela_public.router, prefix="/kalamela", tags=["kalamela-public"])
app.include_router(kalamela_official.router, prefix="/kalamela/official", tags=["kalamela-official"])
app.include_router(kalamela_admin.router, prefix="/kalamela/admin", tags=["kalamela-admin"])


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
