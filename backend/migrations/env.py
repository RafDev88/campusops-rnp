from alembic import context
from app.database import Base, engine
from app import models, domain, discovery_models, orchestration_models, monitor_models

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
