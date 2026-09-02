from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.services.utils import extract_article_no, find_quote, parse_date, split_paragraphs, utcnow
from app.taxonomy import CLAUSE_TYPES, KEYWORD_CATEGORY_HINTS, flatten_categories


PENALTY_HINTS = ["罚款", "责令", "吊销", "刑事责任", "行政处罚", "依法追究", "没收", "警告", "责令改正"]
IMPORTANCE_HINTS = ["罚款", "刑事责任", "吊销", "安全评估", "未经许可", "立即施行"]


def parse_policy_rules(title: str, content: str, issuing_org: str = "") -> dict[str, Any]:
    paragraphs = split_paragraphs(content)
    clauses = _extract_clauses(paragraphs)
    categories = _infer_categories(title + "\n" + content)
    scope = _extract_scope(paragraphs)
    effective = _extract_effective_time(title, content)
    key_articles = []
    for clause in clauses[:8]:
        key_articles.append(
            {
                "article_no": clause["article_no"],
                "summary": clause["text"][:80],
                "source_quote": clause["source_quote"],
            }
        )
    return {
        "effective_time": effective.date().isoformat() if effective else "",
        "policy_level": _guess_level(issuing_org, title),
        "applicable_scope": scope,
        "themes": [item["label"] for item in categories],
        "categories": categories,
        "clauses": clauses,
        "key_articles": key_articles,
        "parser": "rules",
        "evidence_kind": "inference",
        "parsed_at": utcnow().isoformat(),
    }


def analyze_policy_rules(title: str, content: str, structured: dict[str, Any]) -> dict[str, Any]:
    clauses = structured.get("clauses") or []
    mandatory = [c for c in clauses if c.get("clause_type") in {"mandatory", "prohibited"}]
    recommended = [c for c in clauses if c.get("clause_type") == "recommended"]
    core = []
    evidence = []
    for item in (mandatory or clauses)[:5]:
        core.append(
            {
                "text": item.get("text") or item.get("source_quote", "")[:80],
                "article_no": item.get("article_no", ""),
                "source_quote": item.get("source_quote", ""),
                "kind": "inference",
            }
        )
        evidence.append(
            {
                "quote": item.get("source_quote", ""),
                "article_no": item.get("article_no", ""),
                "paragraph_index": item.get("paragraph_index", 0),
                "used_for": "core_requirements",
            }
        )

    penalties = []
    for para_idx, para in enumerate(split_paragraphs(content)):
        if any(hint in para for hint in PENALTY_HINTS):
            penalties.append(
                {
                    "text": para[:120],
                    "source_quote": para[:180],
                    "kind": "fact",
                    "paragraph_index": para_idx,
                }
            )
            if len(penalties) >= 4:
                break
    if not penalties:
        penalties = [
            {
                "text": "原文未直接列明量化罚则，仍可能适用上位法的监督管理与法律责任条款。",
                "source_quote": "",
                "kind": "inference",
            }
        ]

    suggestions = [
        {
            "text": "对照适用主体范围，梳理本企业是否提供生成式/算法/深度合成相关互联网信息服务。",
            "kind": "advice",
        },
        {
            "text": "将强制性条款映射到产品、数据、模型与内容审核流程，形成可勾选的合规清单。",
            "kind": "advice",
        },
        {
            "text": "对原文中的备案、评估、标识、个人信息保护义务设置责任人与完成时限。",
            "kind": "advice",
        },
    ]
    if recommended:
        suggestions.append(
            {
                "text": "将推荐性条款作为增强项纳入内控，不作为最低合规底线。",
                "kind": "advice",
            }
        )

    importance = "high" if any(h in (title + content) for h in IMPORTANCE_HINTS) else "normal"
    return {
        "core_requirements": core,
        "applicable_subjects": structured.get("applicable_scope") or "详见原文适用范围条款",
        "risk_and_penalties": penalties,
        "action_suggestions": suggestions,
        "importance": importance,
        "evidence": evidence,
        "model_name": "rules-v1",
        "generated_at": utcnow().isoformat(),
        "provenance": {
            "fact": ["title", "original_url", "publish_time", "content", "risk_and_penalties(kind=fact)"],
            "inference": ["categories", "clauses", "core_requirements", "applicable_subjects"],
            "advice": ["action_suggestions"],
            "disclaimer": "分析结果不构成法律意见，仅供内部合规研判参考。",
        },
    }


def compare_policies_rules(items: list[dict[str, Any]]) -> dict[str, Any]:
    cat_map: dict[str, list[str]] = {}
    for item in items:
        title = item["title"]
        for cat in item.get("categories") or []:
            key = cat.get("category") if isinstance(cat, dict) else str(cat)
            cat_map.setdefault(key, []).append(title)
    common = []
    for key, titles in cat_map.items():
        if len(set(titles)) >= 2:
            common.append(
                {
                    "text": f"共同覆盖主题：{_label(key)}",
                    "policy_titles": sorted(set(titles)),
                    "kind": "inference",
                }
            )
    differences = []
    for item in items:
        unique = [
            (c.get("category") if isinstance(c, dict) else c)
            for c in (item.get("categories") or [])
            if len(cat_map.get(c.get("category") if isinstance(c, dict) else c, [])) == 1
        ]
        if unique:
            differences.append(
                {
                    "text": "独有主题：" + "、".join(_label(u) for u in unique[:4]),
                    "policy_title": item["title"],
                    "kind": "inference",
                }
            )
        if item.get("effective_time"):
            differences.append(
                {
                    "text": f"生效时间：{item.get('effective_time')}",
                    "policy_title": item["title"],
                    "kind": "fact",
                }
            )
    return {
        "common_requirements": common or [{"text": "主题交叉有限，建议逐份阅读强制性条款。", "kind": "inference"}],
        "differences": differences,
        "provenance": {
            "kind": "inference",
            "disclaimer": "对比基于分类标签与生效时间，不等于法律效力比较。",
        },
    }


def _extract_clauses(paragraphs: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for idx, para in enumerate(paragraphs):
        clause_type = _clause_type(para)
        if not clause_type:
            continue
        if len(para) < 12:
            continue
        results.append(
            {
                "clause_type": clause_type,
                "text": para[:160],
                "article_no": extract_article_no(para),
                "paragraph_index": idx,
                "source_quote": para[:220],
            }
        )
    return results[:40]


def _clause_type(text: str) -> str | None:
    prohibited_kw = next(c for c in CLAUSE_TYPES if c["value"] == "prohibited")["keywords"]
    mandatory_kw = ["应当", "必须"]
    recommended_kw = next(c for c in CLAUSE_TYPES if c["value"] == "recommended")["keywords"]
    if any(k in text for k in prohibited_kw) and re.search(r"(不得|禁止|严禁)", text):
        if any(k in text for k in recommended_kw) and not re.search(r"(不得|禁止|严禁)", text[:20]):
            pass
        else:
            return "prohibited"
    if any(k in text for k in mandatory_kw):
        return "mandatory"
    if any(k in text for k in recommended_kw):
        return "recommended"
    return None


def _infer_categories(text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    parent_of = {c["value"]: c["parent"] for c in flatten_categories()}
    for key, keywords in KEYWORD_CATEGORY_HINTS.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            parent = parent_of.get(key) or key
            subcategory = key if parent_of.get(key) else ""
            category = parent if parent_of.get(key) else key
            token = f"{category}:{subcategory}"
            if token in seen:
                continue
            seen.add(token)
            hits.append({"category": category, "subcategory": subcategory, "label": _label(key)})
    if not hits:
        hits.append({"category": "industry_supervision", "subcategory": "internet_info", "label": "行业监管"})
    return hits[:6]


def _extract_scope(paragraphs: list[str]) -> str:
    for para in paragraphs:
        if "适用" in para[:40] or para.startswith("第二条") or "适用范围" in para:
            return para[:220]
    return paragraphs[1][:220] if len(paragraphs) > 1 else (paragraphs[0][:220] if paragraphs else "")


def _extract_effective_time(title: str, content: str) -> datetime | None:
    patterns = [
        r"自\s*(20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)\s*起施行",
        r"自(20\d{2}-\d{1,2}-\d{1,2})起施行",
        r"(20\d{2}年\d{1,2}月\d{1,2}日)起施行",
    ]
    blob = title + "\n" + content
    for pat in patterns:
        match = re.search(pat, blob)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return datetime.combine(parsed, datetime.min.time())
    return None


def _guess_level(org: str, title: str) -> str:
    text = org + title
    if any(x in text for x in ["市", "北京市", "上海市", "广州市", "深圳市", "杭州市"]):
        if "省" not in org:
            return "municipal"
    if any(x in text for x in ["省", "自治区", "广东省", "浙江省"]):
        return "provincial"
    return "national"


def _label(value: str) -> str:
    from app.taxonomy import category_label

    return category_label(value)
