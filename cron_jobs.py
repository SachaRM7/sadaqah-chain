from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db import Database
from reports import WeeklyReportService


def refresh_nisab_thresholds(db: Database) -> None:
    db.set_setting("nisab_last_refresh", datetime.now(timezone.utc).replace(microsecond=0).isoformat())


def backup_database(db: Database, backup_dir: Path) -> Path:
    filename = f"sadaqahchain-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.sqlite3"
    return db.backup(Path(backup_dir) / filename)


def build_scheduler(db: Database, backup_dir: Path, report_callback: Callable[[str], None] | None = None) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    report_service = WeeklyReportService(db)

    def weekly_report_job() -> None:
        report = report_service.generate_report()
        if report_callback:
            report_callback(report_service.format_report_text(report))

    scheduler.add_job(refresh_nisab_thresholds, CronTrigger(month="1,7", day=1, hour=0, minute=0), args=[db], id="nisab_update", replace_existing=True)
    scheduler.add_job(weekly_report_job, CronTrigger(day_of_week="fri", hour=14, minute=0), id="weekly_report", replace_existing=True)
    scheduler.add_job(backup_database, CronTrigger(hour=2, minute=0), args=[db, backup_dir], id="nightly_backup", replace_existing=True)
    return scheduler
