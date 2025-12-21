import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import get_settings
from app.auth import router as auth_router
from app.units.routers import user as units_user
from app.conference.routers import official as conference_official, public as conference_public
from app.admin.routers import units as admin_units, conference as admin_conference, system as admin_system, site as admin_site
from app.kalamela.routers import public as kalamela_public, official as kalamela_official, admin as kalamela_admin


settings = get_settings()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://csi-webapp-fe.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers - all under /api prefix
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(units_user.router, prefix="/api/units", tags=["units"])
app.include_router(conference_official.router, prefix="/api/conference/official", tags=["conference-official"])
app.include_router(conference_public.router, prefix="/api/conference/public", tags=["conference-public"])
app.include_router(admin_units.router, prefix="/api/admin/units", tags=["admin-units"])
app.include_router(admin_conference.router, prefix="/api/admin/conference", tags=["admin-conference"])
app.include_router(admin_system.router, prefix="/api/admin/system", tags=["admin-system"])
app.include_router(admin_system.router, prefix="/api/admin", tags=["admin-system-alias"])
app.include_router(admin_system.router, prefix="/api/system", tags=["system-alias"])
app.include_router(admin_site.router, prefix="/api", tags=["site-settings"])
app.include_router(kalamela_public.router, prefix="/api/kalamela", tags=["kalamela-public"])
app.include_router(kalamela_official.router, prefix="/api/kalamela/official", tags=["kalamela-official"])
app.include_router(kalamela_admin.router, prefix="/api/kalamela/admin", tags=["kalamela-admin"])


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Health check endpoint that pings the database to keep connections warm."""
    from sqlalchemy import text
    from app.common.db import get_async_engine

    try:
        async with get_async_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"status": "ok", "database": db_status}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
