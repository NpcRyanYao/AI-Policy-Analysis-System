from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("title", "issuing_org", "publish_time", name="uq_policy_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    issuing_org: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    publish_time: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    effective_time: Mapped[date | None] = mapped_column(Date, nullable=True)
    policy_level: Mapped[str] = mapped_column(String(32), nullable=False, default="national", index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, default="manual", index=True)
    original_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    crawl_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ingest_method: Mapped[str] = mapped_column(String(32), nullable=False, default="snapshot")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="raw", index=True)
    snapshot_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    review_flag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    categories: Mapped[list["PolicyCategory"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    clauses: Mapped[list["PolicyClause"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    structured: Mapped["PolicyStructured | None"] = relationship(
        back_populates="policy", cascade="all, delete-orphan", uselist=False
    )
    analysis: Mapped["ComplianceAnalysis | None"] = relationship(
        back_populates="policy", cascade="all, delete-orphan", uselist=False
    )


class PolicyCategory(Base):
    __tablename__ = "policy_categories"
    __table_args__ = (UniqueConstraint("policy_id", "category", "subcategory", name="uq_policy_cat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subcategory: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="categories")


class PolicyClause(Base):
    __tablename__ = "policy_clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    clause_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    article_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    paragraph_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_quote: Mapped[str] = mapped_column(Text, nullable=False, default="")

    policy: Mapped[Policy] = relationship(back_populates="clauses")


class PolicyStructured(Base):
    __tablename__ = "policy_structured"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True)
    applicable_scope: Mapped[str] = mapped_column(Text, nullable=False, default="")
    themes: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    key_articles: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    parser: Mapped[str] = mapped_column(String(32), nullable=False, default="rules")
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="inference")
    parsed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    policy: Mapped[Policy] = relationship(back_populates="structured")


class ComplianceAnalysis(Base):
    __tablename__ = "compliance_analyses"

    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True)
    core_requirements: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    applicable_subjects: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_and_penalties: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    action_suggestions: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    importance: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="rules-v1")
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    policy: Mapped[Policy] = relationship(back_populates="analysis")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("policy_id", name="uq_favorite_policy"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    keywords: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    categories: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    orgs: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="in_app")
    frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="daily")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    policy_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    highlights: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
