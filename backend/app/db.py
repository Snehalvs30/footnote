"""Database connection setup (SQLAlchemy).

engine        ~ a connection pool (like HikariCP in Spring Boot)
Session       ~ a unit of work (like a JPA EntityManager)
get_session() ~ hands one Session to each request, and closes it afterwards
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# pool_pre_ping: check a connection is still alive before using it.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request.

    `yield` makes this a generator: FastAPI runs the code before `yield`,
    gives the session to the endpoint, then resumes after the request to close it.
    The `with` block guarantees the session is closed, even if the request fails.
    """
    with SessionLocal() as session:
        yield session