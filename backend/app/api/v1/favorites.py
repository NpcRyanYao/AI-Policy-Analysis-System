from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.policy import Favorite, Policy
from app.services.export_service import export_excel, export_pdf
from app.services.policy_service import load_policy
from app.services.utils import utcnow

router = APIRouter()


@router.post("/favorites/{policy_id}")
def add_favorite(policy_id: str, db: Session = Depends(get_db)) -> dict:
    load_policy(db, policy_id)
    exists = db.execute(select(Favorite).where(Favorite.policy_id == policy_id)).scalar_one_or_none()
    if not exists:
        db.add(Favorite(policy_id=policy_id, created_at=utcnow()))
        db.commit()
    return {"ok": True, "favorited": True}


@router.delete("/favorites/{policy_id}")
def remove_favorite(policy_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.execute(select(Favorite).where(Favorite.policy_id == policy_id)).scalar_one_or_none()
    if item:
        db.delete(item)
        db.commit()
    return {"ok": True, "favorited": False}


@router.get("/favorites")
def list_favorites(db: Session = Depends(get_db)):
    from app.services.policy_service import favorite_ids, to_list_item

    ids = favorite_ids(db)
    if not ids:
        return []
    rows = (
        db.execute(
            select(Policy)
            .options(selectinload(Policy.categories), selectinload(Policy.analysis))
            .where(Policy.id.in_(ids))
        )
        .scalars()
        .all()
    )
    return [to_list_item(p, ids) for p in rows]


@router.get("/export/excel")
def excel_export(ids: str = Query(default=""), db: Session = Depends(get_db)):
    stmt = select(Policy).options(
        selectinload(Policy.categories),
        selectinload(Policy.analysis),
    )
    if ids:
        stmt = stmt.where(Policy.id.in_(ids.split(",")))
    policies = db.execute(stmt.order_by(Policy.publish_time.desc())).scalars().unique().all()
    data = export_excel(policies)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=policies.xlsx"},
    )


@router.get("/export/pdf/{policy_id}")
def pdf_export(policy_id: str, db: Session = Depends(get_db)):
    policy = load_policy(db, policy_id)
    data = export_pdf(db, policy)
    filename = f"policy-{policy_id[:8]}.pdf"
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
