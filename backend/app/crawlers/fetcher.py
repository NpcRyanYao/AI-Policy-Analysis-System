from __future__ import annotations

import logging
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.config import Settings, get_settings
from app.taxonomy import SOURCE_REGISTRY

logger = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.settings.crawl_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def get_html(self, url: str, timeout: int = 20) -> str:
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        time.sleep(self.settings.crawl_interval_seconds)
        return resp.text


def extract_article(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    content_node = (
        soup.select_one("#UCAP-CONTENT")
        or soup.select_one(".pages_content")
        or soup.select_one(".content")
        or soup.select_one("article")
        or soup.select_one("#content")
        or soup.body
    )
    text = content_node.get_text("\n", strip=True) if content_node else soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    content = "\n".join(lines)
    return {"title": title, "content": content, "original_url": url}


def extract_links(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        text = a.get_text(strip=True)
        if not href or not text or len(text) < 8:
            continue
        if href.startswith("javascript"):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        if urlparse(full).scheme not in {"http", "https"}:
            continue
        seen.add(full)
        items.append({"title": text, "url": full})
    return items[:80]


def crawl_sources(fetcher: Fetcher | None = None, source_id: str | None = None) -> list[dict]:
    fetcher = fetcher or Fetcher()
    collected: list[dict] = []
    sources = SOURCE_REGISTRY
    if source_id:
        sources = [s for s in SOURCE_REGISTRY if s["id"] == source_id]
    for source in sources:
        for list_url in source.get("list_urls") or []:
            try:
                html = fetcher.get_html(list_url)
                links = extract_links(html, list_url)
                for link in links:
                    if not _looks_like_policy(link["title"]):
                        continue
                    collected.append(
                        {
                            "title": link["title"],
                            "original_url": link["url"],
                            "source_id": source["id"],
                            "issuing_org": source["name"],
                            "policy_level": source["level"],
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("抓取列表失败 source=%s url=%s err=%s", source["id"], list_url, exc)
    # 去重 URL
    uniq: dict[str, dict] = {}
    for item in collected:
        uniq[item["original_url"]] = item
    return list(uniq.values())[:40]


def fetch_detail(url: str, fetcher: Fetcher | None = None) -> dict:
    fetcher = fetcher or Fetcher()
    html = fetcher.get_html(url)
    return extract_article(html, url)


def _looks_like_policy(title: str) -> bool:
    keys = ["办法", "规定", "条例", "意见", "通知", "措施", "规范", "标准", "人工智能", "算法", "数据安全", "生成式"]
    return any(k in title for k in keys)
