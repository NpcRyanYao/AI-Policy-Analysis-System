from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Policy Tracker CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="从快照装载数据并解析")
    crawl = sub.add_parser("crawl", help="执行采集（live 或 snapshot）")
    crawl.add_argument("--source", default=None)
    crawl.add_argument("--snapshot-only", action="store_true")
    sub.add_parser("analyze-all", help="对未分析政策重新解析")
    sub.add_parser("digest", help="生成当日订阅日报")
    sub.add_parser("rebuild-index", help="重建全文索引")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    init_db(settings)
    with SessionLocal() as session:
        if args.cmd == "seed":
            from app.services.ingest_service import load_snapshot

            print(json.dumps(load_snapshot(session, settings), ensure_ascii=False, indent=2))
        elif args.cmd == "crawl":
            from app.crawlers.runner import run_crawl

            print(
                json.dumps(
                    run_crawl(session, source_id=args.source, force_snapshot=args.snapshot_only),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        elif args.cmd == "analyze-all":
            from sqlalchemy import select

            from app.models.policy import Policy
            from app.services.analysis_service import parse_and_analyze
            from app.services.search_index import upsert_fts

            policies = session.execute(select(Policy)).scalars().all()
            for policy in policies:
                parse_and_analyze(session, policy, force=True)
                upsert_fts(session, policy)
            session.commit()
            print(f"analyzed={len(policies)}")
        elif args.cmd == "digest":
            from app.services.subscription_service import build_daily_digest

            digest = build_daily_digest(session)
            print(json.dumps({"id": digest.id, "title": digest.title, "summary": digest.summary}, ensure_ascii=False))
        elif args.cmd == "rebuild-index":
            from app.db.session import rebuild_fts

            rebuild_fts(session)
            print("fts rebuilt")


if __name__ == "__main__":
    main()
