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


COMPARE_PROMPT = """对比下列多份政策，返回 JSON：
{{
  "common_requirements": [{{"text": "共同要求", "policy_titles": ["..."], "kind": "inference"}}],
  "differences": [{{"text": "差异点", "policy_title": "...", "kind": "inference"}}]
}}

政策列表：
{bundle}
"""


class LLMClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def available(self) -> bool:
        return self.settings.llm_configured

    def complete_json(self, user_prompt: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return _extract_json(content)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("LLM 调用失败 attempt=%s err=%s", attempt + 1, exc)
        logger.error("LLM 调用最终失败: %s", last_error)
        return None


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
