"""Database session manager for VGNC ORM."""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy.orm import Session

from .factory import SessionFactory


class SessionManager:
    """Manager for handling database sessions with context management."""

    def __init__(self, session_factory: Optional[SessionFactory] = None):
        """Initialize session manager."""
        self.session_factory = session_factory or SessionFactory()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.session_factory.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def get_session_no_commit(self) -> Generator[Session, None, None]:
        """Get a database session without automatic commit."""
        session = self.session_factory.create_session()
        try:
            yield session
        finally:
            session.close()

    def create_session(self) -> Session:
        """Create a new session (manual management required)."""
        return self.session_factory.create_session()

    def health_check(self) -> bool:
        """Perform health check on database connection."""
        return self.session_factory.health_check()

    def close_all_sessions(self) -> None:
        """Close all active sessions."""
        self.session_factory.close_all_sessions()

    def dispose_engine(self) -> None:
        """Dispose the database engine."""
        self.session_factory.dispose_engine()


# Global session manager instance will be initialized lazily
session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """Get or create global session manager instance."""
    global session_manager
    if session_manager is None:
        session_manager = SessionManager()
    return session_manager