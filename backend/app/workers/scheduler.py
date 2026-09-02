from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings, get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _parse_cron(expr: str) -> dict[str, str]:
    minute, hour, day, month, dow = (expr.split() + ["*"] * 5)[:5]
    return {"minute": minute, "hour": hour, "day": day, "month": month, "day_of_week": dow}


def start_scheduler(settings: Settings | None = None) -> BackgroundScheduler | None:
    global _scheduler
    settings = settings or get_settings()
    if not settings.scheduler_enabled:
        logger.info("调度器未启用")
        return None
    if _scheduler:
        return _scheduler
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(_job_crawl, CronTrigger(**_parse_cron(settings.daily_crawl_cron)), id="daily_crawl")
    scheduler.add_job(_job_digest, CronTrigger(**_parse_cron(settings.daily_digest_cron)), id="daily_digest")
    scheduler.start()
    _scheduler = scheduler
    logger.info("调度器已启动")
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _job_crawl() -> None:
    from app.crawlers.runner import run_crawl

    with SessionLocal() as session:
        try:
            run_crawl(session)
        except Exception:
            logger.exception("定时采集失败")


def _job_digest() -> None:
    from app.services.subscription_service import build_daily_digest

    with SessionLocal() as session:
        try:
            build_daily_digest(session)
        except Exception:
            logger.exception("定时日报失败")
