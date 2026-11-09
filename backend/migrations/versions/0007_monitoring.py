"""Durable public endpoint and catalogue-link monitoring."""
from alembic import op
from app.database import Base
from app import monitor_models

revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

def upgrade():Base.metadata.create_all(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Restore a backup to preserve endpoint monitoring history.')
