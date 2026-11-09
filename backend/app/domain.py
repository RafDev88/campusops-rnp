"""Persistent domain for the operations platform; legacy tables are retained."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginLimit(Base):
    __tablename__ = 'login_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SessionToken(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Profile(Base):
    __tablename__ = 'institution_profiles'
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), primary_key=True)
    watched: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    institution: Mapped['Institution'] = relationship('Institution')


class Publication(Base):
    __tablename__ = 'publications'
    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    openalex_id: Mapped[str] = mapped_column(String(200), unique=True)
    doi: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_oa: Mapped[bool] = mapped_column(Boolean, default=False)
    citations: Mapped[int] = mapped_column(default=0)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    affiliations: Mapped[list] = mapped_column(JSON, default=list)
    openalex: Mapped[dict] = mapped_column(JSON, default=dict)
    crossref: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    crossref_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crossref_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkInstitution(Base):
    __tablename__ = 'work_institutions'
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'), primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), primary_key=True)


class Researcher(Base):
    __tablename__ = 'researchers'
    orcid: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    data: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Dataset(Base):
    __tablename__ = 'datasets'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    portal: Mapped[str] = mapped_column(String(100), default='UFRN')
    url: Mapped[str] = mapped_column(Text)
    modified: Mapped[str] = mapped_column(String(100), default='')
    resources: Mapped[list] = mapped_column(JSON, default=list)
    fingerprint: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default='queued')
    active_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records: Mapped[int] = mapped_column(default=0)
    new: Mapped[int] = mapped_column(default=0)
    updated: Mapped[int] = mapped_column(default=0)
    rejected: Mapped[int] = mapped_column(default=0)
    duration_ms: Mapped[int] = mapped_column(default=0)
    attempts: Mapped[int] = mapped_column(default=0)
    http_calls: Mapped[int] = mapped_column(default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    message: Mapped[str] = mapped_column(Text, default='Aguardando worker.')
    error_code: Mapped[str] = mapped_column(String(50), default='')
    actor: Mapped[str] = mapped_column(String(100), default='scheduler')


class Schedule(Base):
    __tablename__ = 'schedules'
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    interval_minutes: Mapped[int] = mapped_column(default=1440)
    next_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)


class Webhook(Base):
    __tablename__ = 'webhooks'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Rule(Base):
    __tablename__ = 'rules'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(30), default='all')
    threshold: Mapped[int] = mapped_column(default=3)
    topic: Mapped[str] = mapped_column(String(150), default='')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_id: Mapped[int | None] = mapped_column(ForeignKey('webhooks.id'), nullable=True)


class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='open')
    active_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Delivery(Base):
    __tablename__ = 'deliveries'
    __table_args__ = (UniqueConstraint('webhook_id', 'event_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    webhook_id: Mapped[int] = mapped_column(ForeignKey('webhooks.id'))
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    attempts: Mapped[int] = mapped_column(default=0)
    next_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    message: Mapped[str] = mapped_column(String(200), default='')


class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
