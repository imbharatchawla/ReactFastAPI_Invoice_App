from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import router
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User
from app.services.rbac import ensure_seed_data

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """
        Serves React app for all non-API routes.

        This allows:
        - /login
        - /dashboard
        - /clients
        - browser refresh on React routes

        API routes like /api/v1/... are already handled above.
        """
        requested_file = STATIC_DIR / full_path

        if full_path and requested_file.exists() and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(STATIC_DIR / "index.html")



@app.on_event("startup")
def startup_seed() -> None:
    """Local-friendly seed: creates base RBAC data and a superadmin if missing."""
    db = SessionLocal()
    try:
        ensure_seed_data(db)
        if not db.query(User).filter(User.email == settings.SUPERADMIN_EMAIL).first():
            db.add(
                User(
                    email=settings.SUPERADMIN_EMAIL,
                    full_name="Super Admin",
                    hashed_password=get_password_hash(settings.SUPERADMIN_PASSWORD),
                    is_superadmin=True,
                )
            )
            db.commit()
    finally:
        db.close()
