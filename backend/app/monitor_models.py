"""Durable endpoint checks, references and rate windows."""
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,JSON,String,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .database import Base
from .domain import utcnow


class MonitorConfig(Base):
    __tablename__='monitor_config'
    id: Mapped[int]=mapped_column(primary_key=True,default=1)
    enabled: Mapped[bool]=mapped_column(default=True)
    discovery: Mapped[bool]=mapped_column(default=True)
    per_day: Mapped[int]=mapped_column(default=2000)
    per_host_minute: Mapped[int]=mapped_column(default=10)
    retention_days: Mapped[int]=mapped_column(default=30)
    next_discovery: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


class MonitorTarget(Base):
    __tablename__='monitor_targets'
    id: Mapped[int]=mapped_column(primary_key=True)
    url_hash: Mapped[str]=mapped_column(String(64),unique=True)
    url: Mapped[str]=mapped_column(Text)
    host: Mapped[str]=mapped_column(String(253),index=True)
    name: Mapped[str]=mapped_column(String(300))
    kind: Mapped[str]=mapped_column(String(30),index=True)
    source: Mapped[str]=mapped_column(String(30),default='')
    expected_type: Mapped[str]=mapped_column(String(20),default='')
    managed: Mapped[bool]=mapped_column(default=False)
    archived: Mapped[bool]=mapped_column(default=False)
    enabled: Mapped[bool]=mapped_column(default=True)
    interval_minutes: Mapped[int]=mapped_column(default=1440)
    next_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    status: Mapped[str]=mapped_column(String(40),default='not_checked',index=True)
    checked_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    last_check_id: Mapped[int|None]=mapped_column(nullable=True)
    failures: Mapped[int]=mapped_column(default=0)
    recoveries: Mapped[int]=mapped_column(default=0)
    alerts: Mapped[bool]=mapped_column(default=True)
    failure_threshold: Mapped[int]=mapped_column(default=3)
    certificate_days: Mapped[int]=mapped_column(default=30)
    webhook_id: Mapped[int|None]=mapped_column(ForeignKey('webhooks.id'),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


class MonitorReference(Base):
    __tablename__='monitor_references'
    target_id: Mapped[int]=mapped_column(ForeignKey('monitor_targets.id'),primary_key=True)
    kind: Mapped[str]=mapped_column(String(30),primary_key=True)
    entity_id: Mapped[str]=mapped_column(String(400),primary_key=True)
    role: Mapped[str]=mapped_column(String(100),primary_key=True)
    title: Mapped[str]=mapped_column(String(500))
    target: Mapped[MonitorTarget]=relationship()


class MonitorCheck(Base):
    __tablename__='monitor_checks'
    id: Mapped[int]=mapped_column(primary_key=True)
    target_id: Mapped[int]=mapped_column(ForeignKey('monitor_targets.id'),index=True)
    active_key: Mapped[str|None]=mapped_column(String(100),unique=True,nullable=True)
    state: Mapped[str]=mapped_column(String(30),default='queued',index=True)
    outcome: Mapped[str]=mapped_column(String(40),default='not_checked')
    ok: Mapped[bool|None]=mapped_column(nullable=True)
    message: Mapped[str]=mapped_column(Text,default='Aguardando verificação.')
    http_status: Mapped[int|None]=mapped_column(nullable=True)
    final_url: Mapped[str]=mapped_column(Text,default='')
    method: Mapped[str]=mapped_column(String(10),default='')
    duration_ms: Mapped[int]=mapped_column(default=0)
    timings: Mapped[dict]=mapped_column(JSON,default=dict)
    redirects: Mapped[list]=mapped_column(JSON,default=list)
    tls: Mapped[dict]=mapped_column(JSON,default=dict)
    actor: Mapped[str]=mapped_column(String(100),default='scheduler')
    manual: Mapped[bool]=mapped_column(default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    lease: Mapped[str]=mapped_column(String(40),default='')
    target: Mapped[MonitorTarget]=relationship()


class MonitorUsage(Base):
    __tablename__='monitor_usage'
    scope: Mapped[str]=mapped_column(String(260),primary_key=True)
    window: Mapped[str]=mapped_column(String(30),primary_key=True)
    count: Mapped[int]=mapped_column(default=0)
