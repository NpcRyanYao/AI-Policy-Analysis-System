from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm.client import (
    ANALYSIS_PROMPT,
    COMPARE_PROMPT,
    PARSE_PROMPT,
    LLMClient,
    normalize_compare_payload,
)
from app.models.policy import ComplianceAnalysis, Policy, PolicyCategory, PolicyClause, PolicyStructured
from app.services.rule_engine import analyze_policy_rules, compare_policies_rules, parse_policy_rules
from app.services.utils import parse_date, utcnow

logger = logging.getLogger(__name__)


def parse_and_analyze(session: Session, policy: Policy, *, force: bool = False) -> Policy:
    settings = get_settings()
    llm = LLMClient(settings)
    # 结构化用规则引擎，避免一次刷新连续打两次大模型导致前端超时
    structured_raw = parse_policy_rules(policy.title, policy.content, policy.issuing_org)

    _apply_structured(session, policy, structured_raw)

    analysis_raw = None
    if llm.available:
        analysis_raw = llm.complete_json(
            ANALYSIS_PROMPT.format(
                title=policy.title,
                structured=structured_raw,
                content=policy.content[:4000],
            ),
            retries=0,
            timeout=max(settings.llm_timeout_seconds, 120),
        )
    if not analysis_raw:
        analysis_raw = analyze_policy_rules(policy.title, policy.content, structured_raw)
        analysis_raw["model_name"] = "rules-v1"
    else:
        analysis_raw.setdefault("model_name", settings.llm_model)
        analysis_raw.setdefault(
            "provenance",
            {
                "fact": ["title", "original_url", "publish_time", "content"],
                "inference": ["core_requirements", "categories"],
                "advice": ["action_suggestions"],
                "disclaimer": "分析结果不构成法律意见，仅供内部合规研判参考。",
            },
        )
        analysis_raw["provenance"]["llm_provider"] = settings.llm_provider

    _apply_analysis(session, policy, analysis_raw)
    policy.status = "analyzed"
    policy.updated_at = utcnow()
    if structured_raw.get("effective_time") and not policy.effective_time:
        policy.effective_time = parse_date(structured_raw.get("effective_time"))
    if structured_raw.get("policy_level"):
        policy.policy_level = structured_raw["policy_level"]
    session.flush()
    return policy


def compare_policies(session: Session, policies: list[Policy]) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    bundle_items = []
    for policy in policies:
        cats = [{"category": c.category, "subcategory": c.subcategory} for c in policy.categories]
        bundle_items.append(
            {
                "title": policy.title,
                "effective_time": policy.effective_time.isoformat() if policy.effective_time else "",
                "categories": cats,
                "summary": policy.summary,
            }
        )
    result = None
    llm_used = False
    if llm.available:
        raw = llm.complete_json(COMPARE_PROMPT.format(bundle=bundle_items), retries=0)
        result = normalize_compare_payload(raw)
        llm_used = result is not None
        if raw and not result:
            logger.warning("对比模型 JSON 缺少可展示字段，回退规则引擎 keys=%s", list(raw.keys()))
    if not result:
        result = compare_policies_rules(bundle_items)
        llm_used = False
    result["provenance"] = result.get("provenance") or {"kind": "inference"}
    result["provenance"]["llm_used"] = llm_used
    return result


def _apply_structured(session: Session, policy: Policy, data: dict) -> None:
    # 走 ORM 集合删除，避免 bulk delete 后 policy.categories 仍引用已删除实例
    policy.categories.clear()
    policy.clauses.clear()
    session.flush()
    for item in data.get("categories") or []:
        policy.categories.append(
            PolicyCategory(
                category=item.get("category") or "industry_supervision",
                subcategory=item.get("subcategory") or "",
            )
        )
    for item in data.get("clauses") or []:
        policy.clauses.append(
            PolicyClause(
                clause_type=item.get("clause_type") or "mandatory",
                text=item.get("text") or "",
                article_no=item.get("article_no") or "",
                paragraph_index=int(item.get("paragraph_index") or 0),
                source_quote=item.get("source_quote") or item.get("text") or "",
            )
        )
    structured = session.get(PolicyStructured, policy.id)
    now = utcnow()
    parsed_at = now
    if data.get("parsed_at"):
        try:
            parsed_at = datetime.fromisoformat(str(data["parsed_at"]).replace("Z", ""))
        except ValueError:
            parsed_at = now
    payload = dict(
        applicable_scope=data.get("applicable_scope") or "",
        themes=data.get("themes") or [],
        key_articles=data.get("key_articles") or [],
        parser=data.get("parser") or ("llm" if get_settings().llm_configured else "rules"),
        evidence_kind=data.get("evidence_kind") or "inference",
        parsed_at=parsed_at,
    )
    if structured:
        for key, value in payload.items():
            setattr(structured, key, value)
    else:
        session.add(PolicyStructured(policy_id=policy.id, **payload))


def _apply_analysis(session: Session, policy: Policy, data: dict) -> None:
    generated_at = utcnow()
    if data.get("generated_at"):
        try:
            generated_at = datetime.fromisoformat(str(data["generated_at"]).replace("Z", ""))
        except ValueError:
            pass
    payload = dict(
        core_requirements=data.get("core_requirements") or [],
        applicable_subjects=data.get("applicable_subjects") or "",
        risk_and_penalties=data.get("risk_and_penalties") or [],
        action_suggestions=data.get("action_suggestions") or [],
        evidence=data.get("evidence") or [],
        importance=data.get("importance") or "normal",
        model_name=data.get("model_name") or "rules-v1",
        generated_at=generated_at,
        provenance=data.get("provenance") or {},
    )
    existing = session.get(ComplianceAnalysis, policy.id)
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
    else:
        session.add(ComplianceAnalysis(policy_id=policy.id, **payload))
    if payload["core_requirements"] and not policy.summary:
        first = payload["core_requirements"][0]
        policy.summary = first.get("text") if isinstance(first, dict) else str(first)
