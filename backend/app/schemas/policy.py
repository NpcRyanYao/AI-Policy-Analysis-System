from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class CategoryOut(BaseModel):
    category: str
    subcategory: str = ""
    label: str = ""


class ClauseOut(BaseModel):
    clause_type: str
    text: str
    article_no: str = ""
    paragraph_index: int = 0
    source_quote: str = ""


class StructuredOut(BaseModel):
    applicable_scope: str = ""
    themes: list[str] = Field(default_factory=list)
    key_articles: list[dict[str, Any]] = Field(default_factory=list)
    parser: str = "rules"
    evidence_kind: Literal["fact", "inference", "advice"] = "inference"
    parsed_at: datetime | None = None


class EvidenceItem(BaseModel):
    quote: str
    article_no: str = ""
    paragraph_index: int = 0
    used_for: str = ""


class AnalysisOut(BaseModel):
    core_requirements: list[dict[str, Any]] = Field(default_factory=list)
    applicable_subjects: str = ""
    risk_and_penalties: list[dict[str, Any]] = Field(default_factory=list)
    action_suggestions: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    importance: str = "normal"
    model_name: str = "rules-v1"
    generated_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class PolicyListItem(BaseModel):
    id: str
    title: str
    issuing_org: str
    publish_time: date | None
    effective_time: date | None
    policy_level: str
    source_id: str
    original_url: str
    summary: str
    categories: list[CategoryOut]
    crawl_time: datetime
    ingest_method: str
    status: str
    importance: str = "normal"
    favorited: bool = False


class PolicyDetail(PolicyListItem):
    content: str
    content_hash: str
    snapshot_id: str | None = None
    review_flag: str | None = None
    clauses: list[ClauseOut] = Field(default_factory=list)
    structured: StructuredOut | None = None
    analysis: AnalysisOut | None = None
    created_at: datetime
    updated_at: datetime


class PolicySearchQuery(BaseModel):
    q: str = ""
    title: str = ""
    policy_level: str | None = None
    issuing_org: str | None = None
    category: str | None = None
    clause_type: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort: Literal["publish_time", "relevance"] = "publish_time"
    page: int = 1
    page_size: int = 10


class PaginatedPolicies(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PolicyListItem]


class ManualIngestIn(BaseModel):
    url: HttpUrl
    title: str | None = None
    issuing_org: str | None = None
    publish_time: date | None = None
    policy_level: str | None = None
    source_id: str = "manual"
    content: str | None = None

    @field_validator("title", "issuing_org", "policy_level", "content", mode="before")
    @classmethod
    def _blank_str_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("publish_time", mode="before")
    @classmethod
    def _blank_date_to_none(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        return value


class SubscriptionIn(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    orgs: list[str] = Field(default_factory=list)
    channel: Literal["in_app", "email"] = "in_app"
    frequency: Literal["daily"] = "daily"
    email: str | None = None
    is_active: bool = True


class SubscriptionOut(SubscriptionIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    digest_date: date
    title: str
    summary: str
    policy_ids: list[str]
    highlights: list[dict[str, Any]]
    created_at: datetime


class DashboardOut(BaseModel):
    total: int
    today_new: int
    by_category: list[dict[str, Any]]
    by_level: list[dict[str, Any]]
    latest: list[PolicyListItem]
    tags: list[dict[str, Any]]
    data_mode: str
    snapshot_id: str
    crawled_at: datetime | None = None
    llm_ready: bool = False


class CompareIn(BaseModel):
    policy_ids: list[str] = Field(min_length=2, max_length=5)


class CompareOut(BaseModel):
    common_requirements: list[dict[str, Any]]
    differences: list[dict[str, Any]]
    policies: list[PolicyListItem]
    provenance: dict[str, Any]


class HealthOut(BaseModel):
    status: str
    version: str
    data_mode: str
    snapshot_id: str
    policy_count: int
    llm_ready: bool
    scheduler_enabled: bool
    time: datetime
