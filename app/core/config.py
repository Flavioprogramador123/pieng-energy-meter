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

    # Firebase / Firestore (opcional - backup em nuvem das leituras)
    firebase_enabled: bool = False
    firebase_credentials_path: str | None = None
    firebase_collection: str = "readings"

    # Postgres local de teste (docker-compose.yml) - usado só pelo script de
    # migração / docker compose, não pela app (que le direto DATABASE_URL)
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()

