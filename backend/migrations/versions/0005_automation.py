"""Durable checkpoints, workflows, calendars, policies and reports."""
from alembic import op
from app.database import Base
from app import orchestration_models as m

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError('Restore a backup to preserve checkpoints and generated reports.')
