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
from .services.runtime_settings import get_runtime_settings
from .services.postgres_mirror import flush_sqlite_to_postgres
from .services.instance_lock import acquire_scheduler_lock


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
    app.mount("/home/static", StaticFiles(directory="home/static"), name="home_static")
    app.state.templates = Jinja2Templates(directory="app/templates")

    @app.get("/")
    def root():  # healthcheck
        return {"status": "ok", "name": settings.app_name}

    app.include_router(get_api_router(), prefix=settings.api_prefix)

    # Módulo HOME (controle residencial Tuya) — pasta /home, branch feature/home-module
    from home.router import router as home_router
    app.include_router(home_router, prefix="/home")

    scheduler = PollingScheduler(timezone=settings.scheduler_timezone)

    def _run_postgres_flush():
        rt = get_runtime_settings()
        if not rt.get("postgres_flush_enabled", True):
            print("[postgres_mirror] flush desabilitado nas configuracoes")
            return
        flush_sqlite_to_postgres()

    def reschedule_postgres_flush():
        if not getattr(app.state, "is_scheduler_owner", False):
            return  # instância secundária: não é dona do scheduler, nada a reagendar
        rt = get_runtime_settings()
        minutes = int(rt.get("postgres_flush_interval_minutes") or 30)
        seconds = max(60, minutes * 60)
        if rt.get("postgres_flush_enabled", True):
            scheduler.add_job(_run_postgres_flush, seconds=seconds, id="postgres_flush")
            print(f"[postgres_mirror] job agendado a cada {minutes} min ({seconds}s)")
        else:
            scheduler.remove_job("postgres_flush")
            print("[postgres_mirror] job removido (flush desligado)")

    app.state.reschedule_postgres_flush = reschedule_postgres_flush

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        app.state.is_scheduler_owner = acquire_scheduler_lock()
        if not app.state.is_scheduler_owner:
            print(
                "[instance_lock] outro processo ja e dono dos pollers/flush neste host "
                "(data/.scheduler.lock) - esta instancia serve API/Dashboard mas NAO vai "
                "coletar nem fazer flush, para nao duplicar requisicoes na Tuya/HD."
            )
            return
        scheduler.start()
        scheduler.add_job(lambda: poll_modbus_devices(), seconds=30, id="poll_modbus")
        scheduler.add_job(lambda: poll_modbus_tcp_devices(), seconds=30, id="poll_modbus_tcp")
        scheduler.add_job(lambda: poll_tuya_devices(), seconds=30, id="poll_tuya")  # Tuya REAL data!
        reschedule_postgres_flush()

    @app.on_event("shutdown")
    def on_shutdown():
        scheduler.shutdown()

    return app


app = create_app()

