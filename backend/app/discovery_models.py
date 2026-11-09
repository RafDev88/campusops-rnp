"""Search projections, normalized relationships and user-owned research lists."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from .domain import Publication, utcnow
from .models import Institution


class WorkMetadata(Base):
    __tablename__='work_metadata'
    publication_id: Mapped[str]=mapped_column(ForeignKey('publications.id'),primary_key=True)
    publication: Mapped[Publication]=relationship()
    language: Mapped[str]=mapped_column(String(20),default='',index=True)
    work_type: Mapped[str]=mapped_column(String(80),default='',index=True)
    journal: Mapped[str]=mapped_column(String(500),default='')
    normalized_journal: Mapped[str]=mapped_column(String(500),default='',index=True)
    normalized_abstract: Mapped[str]=mapped_column(Text,default='')
    has_abstract: Mapped[bool]=mapped_column(default=False,index=True)
    has_doi: Mapped[bool]=mapped_column(default=False,index=True)
    is_retracted: Mapped[bool | None]=mapped_column(nullable=True,index=True)


class SearchIdentifier(Base):
    __tablename__='search_identifiers'
    kind: Mapped[str]=mapped_column(String(30),primary_key=True)
    entity_id: Mapped[str]=mapped_column(String(400),primary_key=True)
    value: Mapped[str]=mapped_column(String(500),primary_key=True,index=True)


class InstitutionField(Base):
    __tablename__='institution_fields'
    institution_id: Mapped[str]=mapped_column(ForeignKey('institutions.id'),primary_key=True)
    institution: Mapped[Institution]=relationship()
    field: Mapped[str]=mapped_column(String(30),primary_key=True)
    value: Mapped[str]=mapped_column(String(250),primary_key=True,index=True)
    label: Mapped[str]=mapped_column(String(250))


class SearchDocument(Base):
    __tablename__ = 'search_documents'
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(400), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text, index=True)
    body: Mapped[str] = mapped_column(Text)
    subtitle: Mapped[str] = mapped_column(Text, default='')
    source: Mapped[str] = mapped_column(String(50))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Topic(Base):
    __tablename__ = 'topics'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500), index=True)


class WorkTopic(Base):
    __tablename__ = 'work_topics'
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'), primary_key=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey('topics.id'), primary_key=True)
    publication: Mapped[Publication] = relationship()
    topic: Mapped[Topic] = relationship()


class Author(Base):
    __tablename__ = 'authors'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500), index=True)
    orcid: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)


class WorkAuthor(Base):
    __tablename__ = 'work_authors'
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'), primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('authors.id'), primary_key=True)
    publication: Mapped[Publication] = relationship()
    author: Mapped[Author] = relationship()


class WorkAffiliation(Base):
    __tablename__ = 'work_affiliations'
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'), primary_key=True)
    institution_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    publication: Mapped[Publication] = relationship()


class Favorite(Base):
    __tablename__ = 'favorites'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(400), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedSearch(Base):
    __tablename__ = 'saved_searches'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    filters: Mapped[dict] = mapped_column(JSON)
    alerts_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedMatch(Base):
    __tablename__ = 'saved_matches'
    search_id: Mapped[int] = mapped_column(ForeignKey('saved_searches.id'), primary_key=True)
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'), primary_key=True)


class SearchAlert(Base):
    __tablename__ = 'search_alerts'
    __table_args__ = (UniqueConstraint('search_id', 'publication_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    search_id: Mapped[int] = mapped_column(ForeignKey('saved_searches.id'))
    publication_id: Mapped[str] = mapped_column(ForeignKey('publications.id'))
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
