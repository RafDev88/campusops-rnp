"""Rotate unsuccessful Crossref lookups without marking them as enriched."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    if 'crossref_checked_at' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('publications')}:
        op.add_column('publications', sa.Column('crossref_checked_at', sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text('UPDATE publications SET crossref_checked_at = crossref_at WHERE crossref_at IS NOT NULL AND crossref_checked_at IS NULL'))


def downgrade():
    op.drop_column('publications', 'crossref_checked_at')
