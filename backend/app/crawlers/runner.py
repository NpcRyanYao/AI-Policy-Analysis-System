from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crawlers.fetcher import Fetcher, crawl_sources, fetch_detail
from app.models.policy import Policy
from app.services.analysis_service import parse_and_analyze
from app.services.ingest_service import finish_job, load_snapshot, record_job, upsert_policy_record
from app.services.search_index import upsert_fts

logger = logging.getLogger(__name__)


def run_crawl(session: Session, *, source_id: str | None = None, force_snapshot: bool = False) -> dict:
    settings = get_settings()
    mode = "snapshot" if (force_snapshot or settings.data_mode == "snapshot") else "live"
    job = record_job(session, mode=mode, source_id=source_id)
    try:
        if mode == "snapshot":
            stats = load_snapshot(session, settings, analyze=True)
            finish_job(session, job, status="success", stats=stats)
            return {"job_id": job.id, "mode": mode, **stats}

        fetcher = Fetcher(settings)
        stubs = crawl_sources(fetcher, source_id=source_id)
        created = 0
        failed = 0
        skipped = 0
        errors: list[str] = []
        for stub in stubs:
            try:
                existing = session.execute(
                    select(Policy).where(Policy.original_url == stub["original_url"])
                ).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue
                detail = fetch_detail(stub["original_url"], fetcher)
                payload = {**stub, **detail}
                policy, is_new = upsert_policy_record(
                    session, payload, ingest_method="crawl", snapshot_id=None
                )
                if is_new:
                    parse_and_analyze(session, policy)
                    upsert_fts(session, policy)
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(f"{stub.get('original_url')}: {exc}")
                logger.warning("详情抓取失败 %s", exc)
        session.commit()
        stats = {
            "listed": len(stubs),
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "errors": errors[:8],
        }
        if created == 0:
            logger.warning("实时抓取无新增，回退装载快照")
            snap = load_snapshot(session, settings, analyze=True)
            stats["fallback_snapshot"] = snap
        finish_job(session, job, status="success", stats=stats)
        return {"job_id": job.id, "mode": mode, **stats}
    except Exception as exc:  # noqa: BLE001
        finish_job(session, job, status="failed", stats={}, error=str(exc))
        raise
