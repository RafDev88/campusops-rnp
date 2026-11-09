from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session


def test_migration_preserves_legacy_rows(tmp_path, monkeypatch):
    from app import database
    from app.models import Execution, Institution
    from app.migrate import migrate
    engine = create_engine(f'sqlite:///{tmp_path / "legacy.db"}')
    Institution.__table__.create(engine)
    Execution.__table__.create(engine)
    with Session(engine) as db:
        db.execute(Institution.__table__.insert().values(id='legacy', name='Preservada', country='Brazil'))
        db.add(Execution(status='success', records=20))
        db.commit()
    monkeypatch.setattr(database, 'engine', engine)
    migrate()
    migrate()
    assert 'alembic_version' in inspect(engine).get_table_names()
    assert 'runs' in inspect(engine).get_table_names()
    with Session(engine) as db:
        from app.discovery_models import SearchDocument
        assert db.get(Institution, 'legacy').name == 'Preservada'
        assert db.scalar(select(Execution)).records == 20
        assert db.get(SearchDocument, ('institution','legacy')).title == 'Preservada'
    engine.dispose()
