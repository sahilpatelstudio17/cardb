# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.core.database import engine, Base
# from app.routers import auth, cars, subscriptions, admin

# from app.core.config import settings
# print(settings.DATABASE_URL)

# def create_app() -> FastAPI:
#     app = FastAPI(title="Car Subscription Platform - FastAPI Backend")

#     # CORS middleware
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

#     # include routers
#     app.include_router(auth.router)
#     app.include_router(cars.router)
#     app.include_router(subscriptions.router)
#     app.include_router(admin.router)

#     @app.on_event("startup")
#     def on_startup():
#         # create tables if they don't exist
#         Base.metadata.create_all(bind=engine)

#     return app


# app = create_app()

# from fastapi.middleware.cors import CORSMiddleware

# origins = [
#     "http://localhost:5173",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text

from app.core.database import engine, Base
from app.routers import auth, cars, subscriptions, admin, payments
from app.core.config import settings

print(settings.DATABASE_URL)

# Media directory for uploads
MEDIA_DIR = Path(__file__).parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def create_app() -> FastAPI:
    app = FastAPI(title="Car Subscription Platform - FastAPI Backend")

    # ---------------- CORS ----------------
    # Allow frontend origins during development
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
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    # --------------------------------------

    # Include routers
    app.include_router(auth.router)
    app.include_router(cars.router)
    app.include_router(subscriptions.router)
    app.include_router(payments.router)
    app.include_router(admin.router)

    # Mount static files for uploaded images
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

    # Create DB tables on startup
    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        # Keep schema in sync for existing PostgreSQL databases.
        if settings.DATABASE_URL.startswith("postgresql"):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE subscriptions "
                        "ADD COLUMN IF NOT EXISTS needs_driver BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
                conn.execute(
                    text(
                        "ALTER TABLE subscriptions "
                        "ADD COLUMN IF NOT EXISTS driver_service_details TEXT"
                    )
                )

    return app


# Create app instance
app = create_app()

