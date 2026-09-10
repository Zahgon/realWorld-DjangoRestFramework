"""Database engine, session factory and declarative base."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, object_session, sessionmaker

from config import settings


class Base(DeclarativeBase):
    def delete(self):
        """Remove this row.

        Every model in the original inherited a delete() from its base class, so
        the method is part of the model surface rather than of any one model.
        """
        session = object_session(self)
        if session is None:
            raise RuntimeError('instance is not attached to a session')
        session.delete(self)
        session.commit()


engine = create_engine(settings.database_url(), future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_session():
    """Request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_all():
    # Importing the model modules registers them on the declarative metadata.
    from accounts import models as accounts_models  # noqa: F401
    from articles import models as articles_models  # noqa: F401
    from comments import models as comments_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
