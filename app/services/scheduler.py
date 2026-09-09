from __future__ import annotations
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable


class PollingScheduler:
    def __init__(self, timezone: str = "UTC"):
        self.scheduler = BackgroundScheduler(timezone=timezone)

    def add_job(self, func: Callable, seconds: int, *, id: str):
        self.scheduler.add_job(func, IntervalTrigger(seconds=seconds), id=id, replace_existing=True)

    def remove_job(self, id: str) -> None:
        try:
            self.scheduler.remove_job(id)
        except Exception:
            pass

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)



