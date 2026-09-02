from __future__ import annotations

import logging
from datetime import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.policy import Policy, PolicyCategory
from app.schemas.policy import DashboardOut
from app.services.policy_service import favorite_ids, to_list_item
from app.services.utils import utcnow
from app.taxonomy import category_label, flatten_categories

logger = logging.getLogger(__name__)


def dashboard(session: Session) -> DashboardOut:
    settings = get_settings()
    total = session.execute(select(func.count(Policy.id))).scalar_one()
    today = utcnow().date()
    start = dt.combine(today, dt.min.time())
    today_new = session.execute(
        select(func.count(Policy.id)).where(Policy.crawl_time >= start)
    ).scalar_one()
    cat_rows = session.execute(
        select(PolicyCategory.category, func.count(PolicyCategory.id)).group_by(PolicyCategory.category)
    ).all()
    by_category = [
        {"value": value, "label": category_label(value), "count": count} for value, count in cat_rows
    ]
    level_rows = session.execute(select(Policy.policy_level, func.count(Policy.id)).group_by(Policy.policy_level)).all()
    level_label = {"national": "国家", "provincial": "省", "municipal": "市"}
    by_level = [{"value": v, "label": level_label.get(v, v), "count": c} for v, c in level_rows]
    latest = (
        session.execute(
            select(Policy)
            .options(selectinload(Policy.categories), selectinload(Policy.analysis))
            .order_by(Policy.publish_time.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )
    starred = favorite_ids(session)
    tags = [{"value": c["value"], "label": c["label"]} for c in flatten_categories() if not c["parent"]]
    crawled = session.execute(select(func.max(Policy.crawl_time))).scalar_one()
    return DashboardOut(
        total=total,
        today_new=today_new,
        by_category=by_category,
        by_level=by_level,
        latest=[to_list_item(p, starred) for p in latest],
        tags=tags,
        data_mode=settings.data_mode,
        snapshot_id=settings.snapshot_id,
        crawled_at=crawled,
        llm_ready=settings.llm_configured,
    )
