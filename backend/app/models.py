from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Institution(Base):
    __tablename__ = 'institutions'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(50), default='ROR')


class Execution(Base):
    __tablename__ = 'executions'
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(30))
    records: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(500), default='')
