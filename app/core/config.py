from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Energy Meter Master"
    api_prefix: str = "/api"
    # Fonte única: Postgres nativo (data dir em F: — ver docs/SETUP_POSTGRES_NATIVO_K.md)
    database_url: str = "postgresql://energy_meter:energy_meter_dev_only@localhost:5432/energy_meter"
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

    # Credenciais Postgres (mesmo cluster do DATABASE_URL). Flush SQLite→PG
    # ficou legado — só roda se DATABASE_URL ainda for sqlite.
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_mirror_url: str | None = None  # opcional; senão monta user/pass/db@localhost:5432

    class Config:
        env_file = ".env"


settings = Settings()

