"""Search index, normalized topics/authors and private saved research."""
from alembic import op
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import Base
from app import discovery_models
from app.domain import Dataset, Publication, Researcher
from app.models import Institution
from app.search_index import sync_record

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind, checkfirst=True)
    with Session(bind=bind) as db:
        for model in (Institution, Publication, Researcher, Dataset):
            for item in db.scalars(select(model)).all():
                with db.no_autoflush:
                    sync_record(db, item)
                db.flush()
        db.commit()
    if bind.dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        op.execute('CREATE INDEX IF NOT EXISTS ix_discovery_body_trgm ON search_documents USING gin (body gin_trgm_ops)')
        op.execute('CREATE INDEX IF NOT EXISTS ix_discovery_title_trgm ON search_documents USING gin (normalized_title gin_trgm_ops)')
        op.execute("CREATE INDEX IF NOT EXISTS ix_discovery_fts ON search_documents USING gin (to_tsvector('simple', body))")
        op.execute('CREATE INDEX IF NOT EXISTS ix_publication_year_citations ON publications (year, citations)')


def downgrade():
    raise RuntimeError('Restore a backup to roll back discovery without losing saved research.')
