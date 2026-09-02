from __future__ import annotations

from datetime import date

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.models.policy import Favorite, Policy, PolicyCategory, PolicyClause
from app.schemas.policy import (
    AnalysisOut,
    CategoryOut,
    ClauseOut,
    PolicyDetail,
    PolicyListItem,
    StructuredOut,
)
from app.services.search_index import search_policy_ids
from app.taxonomy import category_label


def load_policy(session: Session, policy_id: str) -> Policy:
    policy = (
        session.execute(
            select(Policy)
            .options(
                selectinload(Policy.categories),
                selectinload(Policy.clauses),
                selectinload(Policy.structured),
                selectinload(Policy.analysis),
            )
            .where(Policy.id == policy_id)
        )
        .scalar_one_or_none()
    )
    if not policy:
        raise NotFoundError("政策不存在")
    return policy


def favorite_ids(session: Session) -> set[str]:
    rows = session.execute(select(Favorite.policy_id)).scalars().all()
    return set(rows)


def to_list_item(policy: Policy, starred: set[str] | None = None) -> PolicyListItem:
    starred = starred or set()
    importance = policy.analysis.importance if policy.analysis else "normal"
    return PolicyListItem(
        id=policy.id,
        title=policy.title,
        issuing_org=policy.issuing_org,
        publish_time=policy.publish_time,
        effective_time=policy.effective_time,
        policy_level=policy.policy_level,
        source_id=policy.source_id,
        original_url=policy.original_url,
        summary=policy.summary or (policy.content[:160] if policy.content else ""),
        categories=[
            CategoryOut(
                category=c.category,
                subcategory=c.subcategory,
                label=category_label(c.subcategory or c.category),
            )
            for c in policy.categories
        ],
        crawl_time=policy.crawl_time,
        ingest_method=policy.ingest_method,
        status=policy.status,
        importance=importance,
        favorited=policy.id in starred,
    )


def to_detail(policy: Policy, starred: set[str] | None = None) -> PolicyDetail:
    base = to_list_item(policy, starred).model_dump()
    structured = None
    if policy.structured:
        structured = StructuredOut(
            applicable_scope=policy.structured.applicable_scope,
            themes=policy.structured.themes or [],
            key_articles=policy.structured.key_articles or [],
            parser=policy.structured.parser,
            evidence_kind=policy.structured.evidence_kind,  # type: ignore[arg-type]
            parsed_at=policy.structured.parsed_at,
        )
    analysis = None
    if policy.analysis:
        analysis = AnalysisOut(
            core_requirements=policy.analysis.core_requirements or [],
            applicable_subjects=policy.analysis.applicable_subjects,
            risk_and_penalties=policy.analysis.risk_and_penalties or [],
            action_suggestions=policy.analysis.action_suggestions or [],
            evidence=policy.analysis.evidence or [],
            importance=policy.analysis.importance,
            model_name=policy.analysis.model_name,
            generated_at=policy.analysis.generated_at,
            provenance=policy.analysis.provenance or {},
        )
    return PolicyDetail(
        **base,
        content=policy.content,
        content_hash=policy.content_hash,
        snapshot_id=policy.snapshot_id,
        review_flag=policy.review_flag,
        clauses=[
            ClauseOut(
                clause_type=c.clause_type,
                text=c.text,
                article_no=c.article_no,
                paragraph_index=c.paragraph_index,
                source_quote=c.source_quote,
            )
            for c in policy.clauses
        ],
        structured=structured,
        analysis=analysis,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def search_policies(
    session: Session,
    *,
    q: str = "",
    title: str = "",
    policy_level: str | None = None,
    issuing_org: str | None = None,
    category: str | None = None,
    clause_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = "publish_time",
    page: int = 1,
    page_size: int = 10,
) -> tuple[int, list[Policy]]:
    stmt = select(Policy).options(
        selectinload(Policy.categories),
        selectinload(Policy.analysis),
    )
    conditions = []
    fts_ids: list[str] | None = None
    if q.strip():
        fts_ids = search_policy_ids(session, q.strip(), title_only=False)
        if not fts_ids:
            return 0, []
        conditions.append(Policy.id.in_(fts_ids))
    if title.strip():
        title_ids = search_policy_ids(session, title.strip(), title_only=True)
        if not title_ids:
            conditions.append(Policy.title.contains(title.strip()))
        else:
            conditions.append(Policy.id.in_(title_ids))
    if policy_level:
        conditions.append(Policy.policy_level == policy_level)
    if issuing_org:
        conditions.append(Policy.issuing_org.contains(issuing_org))
    if date_from:
        conditions.append(Policy.publish_time >= date_from)
    if date_to:
        conditions.append(Policy.publish_time <= date_to)
    if category:
        stmt = stmt.join(PolicyCategory)
        conditions.append(
            or_(PolicyCategory.category == category, PolicyCategory.subcategory == category)
        )
    if clause_type:
        stmt = stmt.join(PolicyClause, isouter=False)
        conditions.append(PolicyClause.clause_type == clause_type)
    if conditions:
        stmt = stmt.where(and_(*conditions)).distinct()

    count_stmt = select(Policy.id)
    if category:
        count_stmt = count_stmt.join(PolicyCategory)
    if clause_type:
        count_stmt = count_stmt.join(PolicyClause)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions)).distinct()
    total = len(session.execute(count_stmt).scalars().all())

    if sort == "relevance" and fts_ids:
        policies = session.execute(stmt).scalars().unique().all()
        order = {pid: i for i, pid in enumerate(fts_ids)}
        policies.sort(key=lambda p: order.get(p.id, 9999))
        start = (page - 1) * page_size
        return total, policies[start : start + page_size]

    stmt = stmt.order_by(desc(Policy.publish_time), desc(Policy.crawl_time))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = session.execute(stmt).scalars().unique().all()
    return total, items
