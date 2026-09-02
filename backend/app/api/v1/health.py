from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import __version__
from app.config import get_settings
from app.db.session import get_db
from app.models.policy import Policy
from app.schemas.policy import HealthOut
from app.services.utils import utcnow

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    settings = get_settings()
    count = db.execute(select(func.count(Policy.id))).scalar_one()
    return HealthOut(
        status="ok",
        version=__version__,
        data_mode=settings.data_mode,
        snapshot_id=settings.snapshot_id,
        policy_count=count,
        llm_ready=settings.llm_configured,
        scheduler_enabled=settings.scheduler_enabled,
        time=utcnow(),
    )


@router.get("/meta")
def meta():
    from app.taxonomy import CATEGORY_TREE, CLAUSE_TYPES, POLICY_LEVELS, SOURCE_REGISTRY, flatten_categories

    return {
        "categories": CATEGORY_TREE,
        "flat_categories": flatten_categories(),
        "clause_types": CLAUSE_TYPES,
        "policy_levels": POLICY_LEVELS,
        "sources": SOURCE_REGISTRY,
        "generated_at": datetime.utcnow().isoformat(),
    }
