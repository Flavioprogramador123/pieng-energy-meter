from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Energy Meter Master"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/app.db"
    enable_forwarding: bool = True
    forwarder_url: str | None = None
    scheduler_timezone: str = "UTC"
    
    # Tuya IoT Configuration (opcional)
    tuya_access_id: str | None = None
    tuya_access_secret: str | None = None
    tuya_api_region: str = "us"
    tuya_project_code: str | None = None  # só referência; API usa access_id/secret

    # Firebase / Firestore (opcional - backup em nuvem das leituras)
    firebase_enabled: bool = False
    firebase_credentials_path: str | None = None
    firebase_collection: str = "readings"

    # Postgres espelho no HD K: (flush SQLite -> Postgres). A app hot path
    # continua em DATABASE_URL (SQLite). Ver docs/SETUP_POSTGRES_NATIVO_K.md
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_mirror_url: str | None = None  # opcional; senão monta user/pass/db@localhost:5432

    class Config:
        env_file = ".env"


settings = Settings()

