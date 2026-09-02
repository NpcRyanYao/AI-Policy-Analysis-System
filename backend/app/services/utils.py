from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any

import jieba


ARTICLE_RE = re.compile(r"第[一二三四五六七八九十百零〇0-9]+条")
DATE_RE = re.compile(r"(20\d{2})[年\-/.](\d{1,2})[月\-/.](\d{1,2})")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


def sha256_text(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update((part or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def split_paragraphs(content: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n+", content or "") if p.strip()]
    return parts


def extract_article_no(text: str) -> str:
    match = ARTICLE_RE.search(text or "")
    return match.group(0) if match else ""


def parse_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    match = DATE_RE.search(text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def tokenize_for_fts(*texts: str) -> str:
    joined = " ".join(t for t in texts if t)
    tokens = [tok.strip() for tok in jieba.cut_for_search(joined) if tok.strip()]
    return " ".join(tokens)


def json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def snippet(text: str, length: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:length] + ("…" if len(compact) > length else "")


def find_quote(content: str, needle: str) -> tuple[str, int]:
    paragraphs = split_paragraphs(content)
    for idx, para in enumerate(paragraphs):
        if needle and needle[:20] in para:
            return para[:180], idx
    if needle:
        return needle[:180], 0
    return "", 0
