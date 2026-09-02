from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.schemas.policy import AnalysisOut, CompareIn, CompareOut
from app.services.analysis_service import compare_policies, parse_and_analyze
from app.services.policy_service import favorite_ids, load_policy, to_detail, to_list_item
from app.services.search_index import upsert_fts

router = APIRouter()


@router.post("/policies/{policy_id}/analyze", response_model=AnalysisOut)
def refresh_analysis(
    policy_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> AnalysisOut:
    policy = load_policy(db, policy_id)
    parse_and_analyze(db, policy, force=True)
    upsert_fts(db, policy)
    db.commit()
    detail = to_detail(load_policy(db, policy_id), favorite_ids(db))
    assert detail.analysis is not None
    return detail.analysis


@router.post("/policies/compare", response_model=CompareOut)
def compare(body: CompareIn, db: Session = Depends(get_db)) -> CompareOut:
    policies = [load_policy(db, pid) for pid in body.policy_ids]
    result = compare_policies(db, policies)
    starred = favorite_ids(db)
    return CompareOut(
        common_requirements=result.get("common_requirements") or [],
        differences=result.get("differences") or [],
        policies=[to_list_item(p, starred) for p in policies],
        provenance=result.get("provenance") or {},
    )
