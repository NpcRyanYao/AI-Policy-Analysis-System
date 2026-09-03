from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是中国人工智能监管政策分析助手。只依据用户提供的政策原文作答，禁止编造未出现的条款。
输出必须是合法 JSON，不要 Markdown。所有结论必须带原文摘录。
区分三类信息：
- fact: 原文明确写出的事实
- inference: 基于原文的结构化归纳
- advice: 面向企业的通用行动建议，不构成法律意见
"""


PARSE_PROMPT = """请从下列政策原文提取结构化信息，返回 JSON：
{{
  "effective_time": "YYYY-MM-DD 或空字符串",
  "policy_level": "national|provincial|municipal",
  "applicable_scope": "适用范围摘要",
  "themes": ["主题1"],
  "categories": [{{"category": "generative_ai|algorithm_filing|data_security|personal_info|ai_ethics|industry_supervision", "subcategory": "子类英文key"}}],
  "clauses": [{{"clause_type": "mandatory|recommended|prohibited", "text": "条款摘要", "article_no": "第X条", "source_quote": "原文摘录"}}],
  "key_articles": [{{"article_no": "第X条", "summary": "要点", "source_quote": "原文摘录"}}]
}}

标题：{title}
发文机构：{org}
原文：
{content}
"""


ANALYSIS_PROMPT = """基于下列政策原文与结构化信息，生成通用合规影响摘要。返回 JSON：
{{
  "core_requirements": [{{"text": "要求", "article_no": "第X条", "source_quote": "原文", "kind": "inference"}}],
  "applicable_subjects": "适用主体",
  "risk_and_penalties": [{{"text": "风险或处罚", "source_quote": "原文", "kind": "fact"}}],
  "action_suggestions": [{{"text": "通用行动建议", "kind": "advice"}}],
  "importance": "high|normal",
  "evidence": [{{"quote": "原文", "article_no": "第X条", "used_for": "core_requirements"}}]
}}
约束：建议必须标注 kind=advice；不得输出针对特定企业的法律意见。

标题：{title}
结构化：{structured}
原文：
{content}
"""


COMPARE_PROMPT = """对比下列多份政策，只返回 JSON 对象，不要 Markdown，不要 ok/status 这类外壳。
字段必须使用英文键，数组元素必须含 text：
{{
  "common_requirements": [{{"text": "共同要求", "policy_titles": ["政策标题"], "kind": "inference"}}],
  "differences": [{{"text": "差异点", "policy_title": "政策标题", "kind": "inference"}}]
}}
common_requirements 与 differences 至少各有 1 条。

政策列表：
{bundle}
"""


class LLMClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def available(self) -> bool:
        return self.settings.llm_configured

    def complete_json(self, user_prompt: str, *, retries: int | None = None) -> dict[str, Any] | None:
        if not self.available:
            return None
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "stream": False,
        }
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        attempts = (self.settings.llm_max_retries if retries is None else retries) + 1
        for attempt in range(max(1, attempts)):
            try:
                with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                content = _message_text(data)
                parsed = _extract_json(content)
                if not isinstance(parsed, dict) or not parsed:
                    raise ValueError(f"模型未返回可用 JSON，原文前 200 字：{(content or '')[:200]}")
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("LLM 调用失败 attempt=%s err=%s", attempt + 1, exc)
                if retries == 0:
                    break
        logger.error("LLM 调用最终失败: %s", last_error)
        return None


def _message_text(data: dict[str, Any]) -> str:
    message = (data.get("choices") or [{}])[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        content = "".join(parts)
    if not content:
        content = message.get("reasoning_content") or data.get("output_text") or ""
    return str(content or "")


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("模型输出不是 JSON 对象")
    return parsed


def _as_item_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list):
        value = [value]
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            if item.strip():
                rows.append({"text": item.strip()})
            continue
        if not isinstance(item, dict):
            rows.append({"text": str(item)})
            continue
        text = (
            item.get("text")
            or item.get("content")
            or item.get("requirement")
            or item.get("summary")
            or item.get("point")
            or item.get("description")
            or item.get("共同要求")
            or item.get("差异点")
            or ""
        )
        title = item.get("policy_title") or item.get("policy") or item.get("title") or item.get("policy_name") or ""
        row = dict(item)
        row["text"] = str(text).strip()
        if title:
            row["policy_title"] = str(title)
        if row["text"] or row.get("policy_title"):
            rows.append(row)
    return rows


def normalize_compare_payload(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    payload = raw
    for key in ("data", "result", "output", "comparison"):
        inner = payload.get(key)
        if isinstance(inner, dict) and (
            inner.get("common_requirements")
            or inner.get("differences")
            or inner.get("共同要求")
            or inner.get("差异点")
        ):
            payload = inner
            break
    common = _as_item_list(
        payload.get("common_requirements")
        or payload.get("common")
        or payload.get("commons")
        or payload.get("共同要求")
    )
    differences = _as_item_list(
        payload.get("differences")
        or payload.get("difference")
        or payload.get("diffs")
        or payload.get("差异点")
        or payload.get("差异")
    )
    if not common and not differences:
        return None
    return {"common_requirements": common, "differences": differences}
