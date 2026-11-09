"""Indexed bibliographic fields, identifiers and institutional facets."""
from alembic import op
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import Base
from app.domain import Publication,Researcher
from app.models import Institution
from app.search_index import sync_record

revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    Base.metadata.create_all(bind,checkfirst=True)
    with Session(bind=bind) as db:
        for model in (Institution,Publication,Researcher):
            for item in db.scalars(select(model)).all():
                with db.no_autoflush:sync_record(db,item)
                db.flush()
        db.commit()

def downgrade():
    raise RuntimeError('Restore a backup to roll back indexed research metadata.')
