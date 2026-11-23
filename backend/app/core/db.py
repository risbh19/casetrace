from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session


def make_engine(url: str) -> Engine:
    if not url.startswith("sqlite:"):
        return create_engine(url, pool_pre_ping=True, hide_parameters=True)
    engine = create_engine(url, connect_args={"check_same_thread": False}, hide_parameters=True)

    @event.listens_for(engine, "connect")
    def sqlite_constraints(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")

    return engine


def session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as db:
        yield db


DB = Annotated[Session, Depends(session, scope="function")]
