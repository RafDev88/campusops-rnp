"""Track the actual claim time, independently of time spent queued."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    if 'started_at' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('runs')}:
        op.add_column('runs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('runs', 'started_at')
