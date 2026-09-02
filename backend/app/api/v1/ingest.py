from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.crawlers.fetcher import Fetcher, fetch_detail
from app.crawlers.runner import run_crawl
from app.db.session import get_db
from app.schemas.policy import ManualIngestIn, PolicyDetail
from app.services.ingest_service import ingest_manual, load_snapshot
from app.services.policy_service import favorite_ids, to_detail

router = APIRouter()


@router.post("/ingest/url", response_model=PolicyDetail)
def ingest_url(
    body: ManualIngestIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> PolicyDetail:
    payload = body.model_dump()
    payload["original_url"] = str(body.url)
    fetched = None
    if not body.content:
        try:
            fetched = fetch_detail(str(body.url), Fetcher())
        except Exception:
            fetched = None
    if body.content:
        payload["content"] = body.content
    policy = ingest_manual(db, payload, fetched)
    return to_detail(policy, favorite_ids(db))


@router.post("/ingest/snapshot")
def ingest_snapshot(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    return load_snapshot(db, analyze=True)


@router.post("/ingest/crawl")
def ingest_crawl(
    source_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict:
    return run_crawl(db, source_id=source_id)
