from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.exceptions import ConflictError
from app.models.policy import CrawlJob, Policy
from app.services.analysis_service import parse_and_analyze
from app.services.search_index import upsert_fts
from app.services.utils import new_id, parse_date, sha256_text, snippet, utcnow
from app.taxonomy import source_by_id

logger = logging.getLogger(__name__)


def find_duplicate(session: Session, title: str, issuing_org: str, publish_time, content_hash: str) -> Policy | None:
    stmt = select(Policy).where(
        Policy.title == title,
        Policy.issuing_org == issuing_org,
        Policy.publish_time == publish_time,
    )
    found = session.execute(stmt).scalar_one_or_none()
    if found:
        return found
    if content_hash:
        return session.execute(select(Policy).where(Policy.content_hash == content_hash)).scalar_one_or_none()
    return None


def upsert_policy_record(session: Session, payload: dict, *, ingest_method: str, snapshot_id: str | None) -> tuple[Policy, bool]:
    title = (payload.get("title") or "").strip()
    org = (payload.get("issuing_org") or "").strip()
    publish_time = parse_date(payload.get("publish_time"))
    content = payload.get("content") or ""
    content_hash = payload.get("content_hash") or sha256_text(title, org, content)
    existing = find_duplicate(session, title, org, publish_time, content_hash)
    now = utcnow()
    if existing:
        changed = existing.content_hash != content_hash and content
        if changed:
            existing.content = content
            existing.content_hash = content_hash
            existing.status = "raw"
            existing.updated_at = now
            existing.crawl_time = now
        return existing, False

    policy = Policy(
        id=payload.get("id") or new_id(),
        title=title,
        issuing_org=org,
        publish_time=publish_time,
        effective_time=parse_date(payload.get("effective_time")),
        policy_level=payload.get("policy_level") or "national",
        source_id=payload.get("source_id") or "manual",
        original_url=payload.get("original_url") or "",
        content=content,
        summary=payload.get("summary") or snippet(content),
        content_hash=content_hash,
        crawl_time=parse_datetime(payload.get("crawl_time")) or now,
        ingest_method=ingest_method,
        status="raw",
        snapshot_id=snapshot_id,
        review_flag=payload.get("review_flag"),
        created_at=now,
        updated_at=now,
    )
    if not policy.original_url:
        policy.review_flag = "missing_url"
    session.add(policy)
    session.flush()
    return policy, True


def parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "")).replace(tzinfo=None)
    except ValueError:
        return None


def load_snapshot(session: Session, settings: Settings | None = None, *, analyze: bool = True) -> dict:
    settings = settings or get_settings()
    snapshot_dir = settings.snapshot_dir
    manifest_path = snapshot_dir / "manifest.json"
    policies_path = snapshot_dir / "policies.json"
    if not policies_path.exists():
        raise FileNotFoundError(f"快照不存在: {policies_path}")
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = json.loads(policies_path.read_text(encoding="utf-8"))
    created = 0
    skipped = 0
    analyzed = 0
    for item in items:
        policy, is_new = upsert_policy_record(
            session,
            item,
            ingest_method="snapshot",
            snapshot_id=settings.snapshot_id,
        )
        if is_new:
            created += 1
        else:
            skipped += 1
        if analyze and (is_new or policy.status != "analyzed"):
            parse_and_analyze(session, policy)
            analyzed += 1
        upsert_fts(session, policy)
    session.commit()
    stats = {
        "snapshot_id": settings.snapshot_id,
        "captured_at": manifest.get("captured_at"),
        "created": created,
        "skipped": skipped,
        "analyzed": analyzed,
        "total_in_snapshot": len(items),
    }
    logger.info("snapshot loaded: %s", stats)
    return stats


def ensure_seed_data(session: Session, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    count = session.execute(select(func.count(Policy.id))).scalar_one()
    if count:
        return
    logger.info("数据库为空，自动装载快照 %s", settings.snapshot_id)
    load_snapshot(session, settings, analyze=True)


def ingest_manual(session: Session, payload: dict, fetched: dict | None = None) -> Policy:
    data = dict(payload)
    if fetched:
        data.update({k: v for k, v in fetched.items() if v})
    if not data.get("title") or not data.get("content"):
        raise ConflictError("补录失败：缺少标题或正文")
    policy, is_new = upsert_policy_record(
        session,
        data,
        ingest_method="manual",
        snapshot_id=None,
    )
    if not is_new and policy.content == data.get("content"):
        raise ConflictError("已存在相同政策（标题+发文机构+发布时间）")
    parse_and_analyze(session, policy, force=True)
    upsert_fts(session, policy)
    session.commit()
    session.refresh(policy)
    return policy


def record_job(session: Session, *, mode: str, source_id: str | None = None) -> CrawlJob:
    job = CrawlJob(
        id=new_id(),
        mode=mode,
        status="running",
        source_id=source_id,
        started_at=utcnow(),
        stats={},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def finish_job(session: Session, job: CrawlJob, *, status: str, stats: dict, error: str | None = None) -> None:
    job.status = status
    job.stats = stats
    job.error = error
    job.finished_at = utcnow()
    session.add(job)
    session.commit()


def source_label(source_id: str) -> str:
    src = source_by_id(source_id)
    return src["name"] if src else source_id
