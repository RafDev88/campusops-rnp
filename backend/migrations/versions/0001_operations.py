"""Create the operations schema without changing legacy institutions or executions.

Revision ID: 0001
Revises:
"""
from alembic import op
from app.database import Base
from app import domain, models

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade():
    # Legacy data is intentionally preserved. A destructive rollback is not supported.
    raise RuntimeError('Restore a database backup to roll back this initial migration.')
