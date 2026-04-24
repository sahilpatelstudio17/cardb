from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine, Base, SessionLocal
from app.routers import auth, cars, subscriptions, admin, payments
from app.core.config import settings
from app.models import User
from passlib.context import CryptContext

# ---------------- PASSWORD HASH ----------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)
# ----------------------------------------------

MEDIA_DIR = Path(__file__).parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def create_admin_user():
    db: Session = SessionLocal()
    try:
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD

        if not admin_email or not admin_password:
            print("⚠️ Admin credentials not set")
            return

        existing = db.query(User).filter(User.email == admin_email).first()

        if existing:
            print("ℹ️ Admin already exists")
            return

        admin_user = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_admin=True
        )

        db.add(admin_user)
        db.commit()
        print("✅ Admin user created")

    except Exception as e:
        print("❌ Admin creation failed:", e)
        db.rollback()

    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Car Subscription Platform - FastAPI Backend")

    # ---------------- CORS ----------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://your-frontend.onrender.com"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # --------------------------------------

    # Routers
    app.include_router(auth.router)
    app.include_router(cars.router)
    app.include_router(subscriptions.router)
    app.include_router(payments.router)
    app.include_router(admin.router)

    # Static files
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

    # ---------------- STARTUP ----------------
    @app.on_event("startup")
    def on_startup():
        try:
            Base.metadata.create_all(bind=engine)

            if settings.DATABASE_URL.startswith("postgresql"):
                with engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE subscriptions "
                        "ADD COLUMN IF NOT EXISTS needs_driver BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
                    conn.execute(text(
                        "ALTER TABLE subscriptions "
                        "ADD COLUMN IF NOT EXISTS driver_service_details TEXT"
                    ))

            create_admin_user()

        except Exception as e:
            print("❌ Startup error:", e)

    return app


app = create_app()