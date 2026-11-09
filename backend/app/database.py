import os
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, 'connect')
def sqlite_integrity(connection, record):
    if isinstance(connection, sqlite3.Connection):
        connection.execute('PRAGMA foreign_keys=ON')


url = os.getenv('DATABASE_URL', 'sqlite:///./campus.db')
engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
Session = sessionmaker(engine)
