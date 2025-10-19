from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .core.config import settings
from .core.db import Base, engine
from .routers import get_api_router
from .services.scheduler import PollingScheduler
from .services.pollers import poll_modbus_devices, poll_modbus_tcp_devices
from .services.tuya_poller import poll_tuya_devices


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # templates e estáticos
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.state.templates = Jinja2Templates(directory="app/templates")

    @app.get("/")
    def root():  # healthcheck
        return {"status": "ok", "name": settings.app_name}

    app.include_router(get_api_router(), prefix=settings.api_prefix)

    scheduler = PollingScheduler(timezone=settings.scheduler_timezone)

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        scheduler.start()
        scheduler.add_job(lambda: poll_modbus_devices(), seconds=30, id="poll_modbus")
        scheduler.add_job(lambda: poll_modbus_tcp_devices(), seconds=30, id="poll_modbus_tcp")
        scheduler.add_job(lambda: poll_tuya_devices(), seconds=30, id="poll_tuya")  # Tuya REAL data!

    @app.on_event("shutdown")
    def on_shutdown():
        scheduler.shutdown()

    return app


app = create_app()

