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

    class Config:
        env_file = ".env"


settings = Settings()

