from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.services.utils import tokenize_for_fts


def to_fts_document(policy: Policy) -> dict[str, str]:
    return {
        "policy_id": policy.id,
        "title": tokenize_for_fts(policy.title),
        "issuing_org": tokenize_for_fts(policy.issuing_org),
        "content": tokenize_for_fts(policy.title, policy.issuing_org, policy.content, policy.summary),
    }


def upsert_fts(session: Session, policy: Policy) -> None:
    session.execute(text("DELETE FROM policy_fts WHERE policy_id = :pid"), {"pid": policy.id})
    doc = to_fts_document(policy)
    session.execute(
        text(
            "INSERT INTO policy_fts(policy_id, title, issuing_org, content) "
            "VALUES (:policy_id, :title, :issuing_org, :content)"
        ),
        doc,
    )


def search_policy_ids(session: Session, query: str, title_only: bool = False) -> list[str]:
    tokenized = tokenize_for_fts(query)
    if not tokenized:
        return []
    column = "title" if title_only else "content"
    # FTS5 MATCH; quote tokens to reduce syntax errors
    match = " ".join(tokenized.split())
    rows = session.execute(
        text(
            f"SELECT policy_id FROM policy_fts WHERE {column} MATCH :q "
            "ORDER BY rank LIMIT 200"
        ),
        {"q": match},
    ).fetchall()
    return [row[0] for row in rows]
