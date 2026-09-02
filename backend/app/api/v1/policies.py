from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.policy import Policy
from app.schemas.policy import DashboardOut, PaginatedPolicies, PolicyDetail, PolicyListItem
from app.services.dashboard_service import dashboard
from app.services.policy_service import favorite_ids, load_policy, search_policies, to_detail, to_list_item

router = APIRouter()


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    return dashboard(db)


@router.get("/policies", response_model=PaginatedPolicies)
def list_policies(
    q: str = "",
    title: str = "",
    policy_level: str | None = None,
    issuing_org: str | None = None,
    category: str | None = None,
    clause_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = Query(default="publish_time"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedPolicies:
    from datetime import date

    def _d(v: str | None) -> date | None:
        if not v:
            return None
        return date.fromisoformat(v)

    total, items = search_policies(
        db,
        q=q,
        title=title,
        policy_level=policy_level,
        issuing_org=issuing_org,
        category=category,
        clause_type=clause_type,
        date_from=_d(date_from),
        date_to=_d(date_to),
        sort=sort,
        page=page,
        page_size=page_size,
    )
    starred = favorite_ids(db)
    return PaginatedPolicies(
        total=total,
        page=page,
        page_size=page_size,
        items=[to_list_item(p, starred) for p in items],
    )


@router.get("/policies/{policy_id}", response_model=PolicyDetail)
def get_policy(policy_id: str, db: Session = Depends(get_db)) -> PolicyDetail:
    policy = load_policy(db, policy_id)
    return to_detail(policy, favorite_ids(db))


@router.get("/policies/{policy_id}/related", response_model=list[PolicyListItem])
def related_policies(policy_id: str, db: Session = Depends(get_db)) -> list[PolicyListItem]:
    policy = load_policy(db, policy_id)
    cats = {c.category for c in policy.categories}
    rows = (
        db.execute(
            select(Policy)
            .options(selectinload(Policy.categories), selectinload(Policy.analysis))
            .where(Policy.id != policy_id)
            .order_by(Policy.publish_time.desc())
            .limit(30)
        )
        .scalars()
        .all()
    )
    scored = []
    for item in rows:
        overlap = len(cats.intersection({c.category for c in item.categories}))
        if overlap:
            scored.append((overlap, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    starred = favorite_ids(db)
    return [to_list_item(item, starred) for _, item in scored[:5]]
