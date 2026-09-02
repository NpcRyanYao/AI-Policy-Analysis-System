from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.policy import Digest, Policy, Subscription
from app.services.utils import new_id, utcnow


def create_subscription(session: Session, payload: dict) -> Subscription:
    now = utcnow()
    item = Subscription(
        id=new_id(),
        name=payload["name"],
        keywords=payload.get("keywords") or [],
        categories=payload.get("categories") or [],
        orgs=payload.get("orgs") or [],
        channel=payload.get("channel") or "in_app",
        frequency=payload.get("frequency") or "daily",
        email=payload.get("email"),
        is_active=payload.get("is_active", True),
        created_at=now,
        updated_at=now,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def list_subscriptions(session: Session) -> list[Subscription]:
    return session.execute(select(Subscription).order_by(Subscription.created_at.desc())).scalars().all()


def delete_subscription(session: Session, sub_id: str) -> None:
    item = session.get(Subscription, sub_id)
    if item:
        session.delete(item)
        session.commit()


def match_policies(session: Session, sub: Subscription, policies: list[Policy] | None = None) -> list[Policy]:
    if policies is None:
        policies = (
            session.execute(select(Policy).options(selectinload(Policy.categories)).order_by(Policy.publish_time.desc()))
            .scalars()
            .all()
        )
    matched = []
    for policy in policies:
        if _match(sub, policy):
            matched.append(policy)
    return matched


def _match(sub: Subscription, policy: Policy) -> bool:
    if not sub.is_active:
        return False
    ok = False
    if sub.keywords:
        blob = f"{policy.title}\n{policy.content}"
        if any(k and k in blob for k in sub.keywords):
            ok = True
    cats = {c.category for c in policy.categories} | {c.subcategory for c in policy.categories}
    if sub.categories and cats.intersection(set(sub.categories)):
        ok = True
    if sub.orgs and any(o and o in policy.issuing_org for o in sub.orgs):
        ok = True
    if not sub.keywords and not sub.categories and not sub.orgs:
        ok = True
    return ok


def build_daily_digest(session: Session, day: date | None = None) -> Digest:
    day = day or utcnow().date()
    existing = session.execute(select(Digest).where(Digest.digest_date == day)).scalar_one_or_none()
    policies = (
        session.execute(select(Policy).options(selectinload(Policy.categories), selectinload(Policy.analysis)))
        .scalars()
        .all()
    )
    subs = list_subscriptions(session)
    matched_ids: list[str] = []
    highlights = []
    if subs:
        for sub in subs:
            for policy in match_policies(session, sub, policies):
                if policy.id not in matched_ids:
                    matched_ids.append(policy.id)
                    highlights.append(
                        {
                            "policy_id": policy.id,
                            "title": policy.title,
                            "importance": policy.analysis.importance if policy.analysis else "normal",
                            "subscription": sub.name,
                            "original_url": policy.original_url,
                        }
                    )
    else:
        latest = sorted(policies, key=lambda p: p.crawl_time, reverse=True)[:8]
        for policy in latest:
            matched_ids.append(policy.id)
            highlights.append(
                {
                    "policy_id": policy.id,
                    "title": policy.title,
                    "importance": policy.analysis.importance if policy.analysis else "normal",
                    "subscription": "全部最新",
                    "original_url": policy.original_url,
                }
            )
    high = [h for h in highlights if h.get("importance") == "high"]
    summary = f"{day.isoformat()} 共匹配 {len(matched_ids)} 条政策，其中高亮提醒 {len(high)} 条。"
    if existing:
        existing.title = f"政策动态日报 {day.isoformat()}"
        existing.summary = summary
        existing.policy_ids = matched_ids
        existing.highlights = highlights
        session.commit()
        session.refresh(existing)
        return existing
    digest = Digest(
        id=new_id(),
        digest_date=day,
        title=f"政策动态日报 {day.isoformat()}",
        summary=summary,
        policy_ids=matched_ids,
        highlights=highlights,
        created_at=utcnow(),
    )
    session.add(digest)
    session.commit()
    session.refresh(digest)
    return digest
