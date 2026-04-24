try:
    from pydantic_settings import BaseSettings as _BaseSettings
    _PD_V2 = True
except Exception:
    from pydantic import BaseSettings as _BaseSettings
    _PD_V2 = False


class Settings(_BaseSettings):
    PROJECT_NAME: str = "Car Subscription Platform"

    # ---------------- DATABASE ----------------
    DATABASE_URL: str = "postgresql://postgres:new123@localhost:5432/car_subscription_db"

    # ---------------- SECURITY ----------------
    SECRET_KEY: str = "CHANGE_ME_TO_A_RANDOM_SECRET"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ---------------- ADMIN ----------------
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # ---------------- PAYMENT ----------------
    RAZORPAY_KEY_ID: str = "rzp_test_SeXUaT8dywpUoG"
    RAZORPAY_KEY_SECRET: str = "OipLgVthHoUoZy3bMuXXHJop"

    # ---------------- ENV CONFIG ----------------
    if _PD_V2:
        model_config = {
            "env_file": ".env",
            "extra": "ignore"
        }
    else:
        class Config:
            env_file = ".env"
            extra = "ignore"


settings = Settings()