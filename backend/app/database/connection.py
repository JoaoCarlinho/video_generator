"""Database connection management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Lazy database engine initialization
engine = None
SessionLocal = None


def init_db():
    """Initialize database connection lazily."""
    global engine, SessionLocal
    if engine is None and settings.database_url:
        engine = create_engine(
            settings.database_url,
            poolclass=NullPool,  # Disable connection pooling for Railway
            echo=settings.debug
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )


def get_db() -> Session:
    """Get database session dependency for FastAPI."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Set DATABASE_URL in .env")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Test database connection."""
    if not settings.database_url:
        logger.warning("⚠️  DATABASE_URL not configured")
        return False
    
    try:
        init_db()
        if engine is None:
            logger.warning("⚠️  Could not initialize database engine")
            return False
        
        with engine.begin() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

