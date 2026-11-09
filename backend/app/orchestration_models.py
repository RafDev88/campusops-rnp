"""Durable automation state, independent of Celery message delivery."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from .domain import Run, utcnow


class SourcePolicy(Base):
    __tablename__ = 'source_policies'
    source: Mapped[str] = mapped_column(String(30), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    per_run: Mapped[int] = mapped_column(default=500)
    per_minute: Mapped[int] = mapped_column(default=60)
    per_day: Mapped[int] = mapped_column(default=2000)
    cache_mb: Mapped[int] = mapped_column(default=100)
    auto_retries: Mapped[int] = mapped_column(default=2)
    overlap_days: Mapped[int] = mapped_column(default=2)


class Usage(Base):
    __tablename__ = 'source_usage'
    source: Mapped[str] = mapped_column(String(30), primary_key=True)
    window: Mapped[str] = mapped_column(String(30), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)


class Runtime(Base):
    __tablename__ = 'run_runtime'
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    dispatch_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    requested: Mapped[str] = mapped_column(String(20), default='')
    lease: Mapped[str] = mapped_column(String(40), default='')
    stage: Mapped[str] = mapped_column(String(30), default='queued')
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    responses: Mapped[int] = mapped_column(default=0)
    pages: Mapped[int] = mapped_column(default=0)
    cache_bytes: Mapped[int] = mapped_column(default=0)
    retries: Mapped[int] = mapped_column(default=0)
    next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    run: Mapped[Run] = relationship()


class Checkpoint(Base):
    __tablename__ = 'run_checkpoints'
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunLog(Base):
    __tablename__ = 'run_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunEntity(Base):
    __tablename__ = 'run_entities'
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(400), primary_key=True)


class Watermark(Base):
    __tablename__ = 'source_watermarks'
    scope: Mapped[str] = mapped_column(String(250), primary_key=True)
    date: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Review(Base):
    __tablename__ = 'record_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    active_key: Mapped[str | None] = mapped_column(String(500), unique=True, nullable=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'))
    source: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(400))
    reason: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    retry_run_id: Mapped[int | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Change(Base):
    __tablename__ = 'data_changes'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), index=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(400), index=True)
    field: Mapped[str] = mapped_column(String(80))
    before: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Workflow(Base):
    __tablename__ = 'workflows'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(100))
    steps: Mapped[list] = mapped_column(JSON)
    params: Mapped[dict] = mapped_column(JSON)
    allow_partial: Mapped[bool] = mapped_column(default=True)
    enabled: Mapped[bool] = mapped_column(default=True)


class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey('workflows.id'))
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    dispatch_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    active_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='running')
    step: Mapped[int] = mapped_column(default=0)
    child_id: Mapped[int | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    report_id: Mapped[int | None] = mapped_column(nullable=True)
    requested: Mapped[str] = mapped_column(String(20), default='')
    history: Mapped[list] = mapped_column(JSON, default=list)
    message: Mapped[str] = mapped_column(Text, default='Aguardando primeira etapa.')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportTemplate(Base):
    __tablename__ = 'report_templates'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    filters: Mapped[dict] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(default=True)


class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey('report_templates.id'), nullable=True)
    dispatch_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    filters: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='queued')
    content: Mapped[str] = mapped_column(Text, default='')
    rows: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    message: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarSchedule(Base):
    __tablename__ = 'calendar_schedules'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(30), default='')
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    cron: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(100))
    next_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    enabled: Mapped[bool] = mapped_column(default=True)


class CalendarFire(Base):
    __tablename__ = 'calendar_fires'
    __table_args__ = (UniqueConstraint('schedule_id', 'scheduled_at'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey('calendar_schedules.id'))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default='pending')
    job_id: Mapped[int | None] = mapped_column(nullable=True)
    message: Mapped[str] = mapped_column(Text, default='')
