import asyncio

import httpx
import pytest
from sqlalchemy import func, select

from app.database import Base, Session, engine
from app.models import Execution, Institution
from app.services import synchronize


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app import services

    test_engine = create_engine(f'sqlite:///{tmp_path / "test.db"}')
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(test_engine)
    monkeypatch.setattr(services, 'Session', test_session)
    monkeypatch.setitem(globals(), 'Session', test_session)
    yield
    test_engine.dispose()


class Connector:
    async def fetch(self):
        return [{'id': 'https://ror.org/test', 'name': 'Universidade Teste', 'country': 'Brazil'}]


def test_repeated_import_is_idempotent():
    asyncio.run(synchronize(Connector()))
    asyncio.run(synchronize(Connector()))
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Institution).where(Institution.id == 'https://ror.org/test')) == 1


def test_source_failure_is_recorded():
    class Failing:
        async def fetch(self):
            raise httpx.ConnectError('offline')
    identifier = asyncio.run(synchronize(Failing()))
    with Session() as db:
        assert db.get(Execution, identifier).status == 'failed'
