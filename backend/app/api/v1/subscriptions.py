from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.policy import Digest, Subscription
from app.schemas.policy import DigestOut, SubscriptionIn, SubscriptionOut
from app.services.subscription_service import (
    build_daily_digest,
    create_subscription,
    delete_subscription,
    list_subscriptions,
)

router = APIRouter()


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def get_subs(db: Session = Depends(get_db)) -> list[Subscription]:
    return list_subscriptions(db)


@router.post("/subscriptions", response_model=SubscriptionOut)
def add_sub(body: SubscriptionIn, db: Session = Depends(get_db)) -> Subscription:
    return create_subscription(db, body.model_dump())


@router.delete("/subscriptions/{sub_id}")
def remove_sub(sub_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(Subscription, sub_id)
    if not item:
        raise NotFoundError("订阅不存在")
    delete_subscription(db, sub_id)
    return {"ok": True}


@router.post("/digests/generate", response_model=DigestOut)
def generate_digest(db: Session = Depends(get_db)) -> Digest:
    return build_daily_digest(db)


@router.get("/digests", response_model=list[DigestOut])
def list_digests(db: Session = Depends(get_db)) -> list[Digest]:
    return db.execute(select(Digest).order_by(Digest.digest_date.desc())).scalars().all()
