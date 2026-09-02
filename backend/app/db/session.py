from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.base import Base


def _sqlite_connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception:
        pass


def make_engine(settings: Settings | None = None):
    settings = settings or get_settings()
    db_path = settings.sqlite_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    return create_engine(url, connect_args=_sqlite_connect_args(url), future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS policy_fts USING fts5(
    policy_id UNINDEXED,
    title,
    issuing_org,
    content,
    tokenize = 'unicode61'
);
"""


def ensure_fts(session: Session) -> None:
    session.execute(text(FTS_DDL))
    session.commit()


def rebuild_fts(session: Session) -> None:
    from app.models.policy import Policy
    from app.services.search_index import to_fts_document

    session.execute(text("DROP TABLE IF EXISTS policy_fts"))
    session.execute(text(FTS_DDL))
    policies = session.query(Policy).all()
    for policy in policies:
        doc = to_fts_document(policy)
        session.execute(
            text(
                "INSERT INTO policy_fts(policy_id, title, issuing_org, content) "
                "VALUES (:policy_id, :title, :issuing_org, :content)"
            ),
            doc,
        )
    session.commit()


def init_db(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    Path(settings.runtime_dir).mkdir(parents=True, exist_ok=True)
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        ensure_fts(session)
