"""Public response contracts shared by OpenAPI and runtime serialization."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]
    code: str
    request_id: str


class PublicationResponse(BaseModel):
    # Preserve detailed bibliographic metadata while typing the shared list contract.
    model_config = ConfigDict(extra='allow')
    id: str
    title: str
    year: int | None
    doi: str | None
    is_oa: bool
    citations: int
    topics: list[dict[str, Any]]
    authors: list[dict[str, Any]]
    affiliations: list[dict[str, Any]]
    fetched_at: datetime
    crossref_at: datetime | None
    source: str
    favorite: bool


class SearchFeatures(BaseModel):
    approximate: bool


class PublicationPage(BaseModel):
    total: int
    items: list[PublicationResponse]
    features: SearchFeatures
    scope: str


class SourceStatus(BaseModel):
    source: str
    status: str
    checked_at: datetime | None
    collected_at: datetime | None
    coverage: Literal['partial', 'complete', 'unknown']
    message: str


class CatalogStatus(BaseModel):
    total_publications: int
    sources: list[SourceStatus]
    scope: str


class OperationItem(BaseModel):
    id: str
    kind: str
    title: str
    status: str
    stage: str = ''
    next_at: datetime | None = None
    message: str = ''
    action: str
    route: str
    resource_id: int | None = None


class AutomationOverview(BaseModel):
    active_runs: int
    failed_runs: int
    enabled_schedules: int
    items: list[OperationItem]
    scope: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class SessionInfo(BaseModel):
    id: str
    current: bool
    expires_at: datetime


class SessionList(BaseModel):
    items: list[SessionInfo]


class MessageResponse(BaseModel):
    message: str
