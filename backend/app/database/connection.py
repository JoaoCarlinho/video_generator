"""Database connection management."""

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.config import settings
import logging
import ssl

logger = logging.getLogger(__name__)

# Lazy database engine initialization
engine = None
SessionLocal = None


def init_db():
    """Initialize database connection lazily."""
    global engine, SessionLocal
    
    if engine is not None:
        logger.debug("Database engine already initialized")
        return
    
    if not settings.database_url:
        logger.warning("⚠️  DATABASE_URL not set, cannot initialize database")
        return
    
    try:
        logger.info(f"Initializing database connection...")
        
        # Modify connection string for SSL handling
        db_url = settings.database_url
        if db_url and 'postgresql' in db_url:
            # Check if sslmode is already explicitly set in the URL
            has_explicit_sslmode = 'sslmode=' in db_url

            if not has_explicit_sslmode:
                # Only add sslmode if not already specified
                # Determine if this is a local or remote database
                # Treat VPC private IPs (10.0.x.x) as local since proxy doesn't handle SSL
                # Check for hostname patterns, not just 'postgres' which matches username
                is_local = ('localhost' in db_url or '127.0.0.1' in db_url or
                           '@postgres/' in db_url or '@postgres:' in db_url or '10.0.' in db_url)

                # Add appropriate SSL mode
                if is_local:
                    # Local PostgreSQL - disable SSL
                    if '?' in db_url:
                        db_url += '&sslmode=disable'
                    else:
                        db_url += '?sslmode=disable'
                    logger.debug("🔓 Using non-SSL for local PostgreSQL connection")
                else:
                    # Remote databases - require SSL
                    if '?' in db_url:
                        db_url += '&sslmode=require'
                    else:
                        db_url += '?sslmode=require'
                    logger.debug("🔒 Using SSL for remote PostgreSQL connection")
            else:
                logger.debug("📌 Using explicitly configured sslmode from DATABASE_URL")
        
        # Configure connection arguments
        is_local = ('localhost' in db_url or '127.0.0.1' in db_url or
                   '@postgres/' in db_url or '@postgres:' in db_url or '10.0.' in db_url)

        connect_args = {
            'connect_timeout': 10,
            'options': '-c client_encoding=UTF8'
        }

        if is_local:
            connect_args['sslmode'] = 'disable'

        # Using Supabase transaction pooler for IPv4 compatibility
        logger.info("🔧 Connecting to database via Supabase pooler")

        engine = create_engine(
            db_url,
            poolclass=NullPool,  # Disable connection pooling for serverless
            echo=settings.debug,
            connect_args=connect_args
        )
        
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("✅ Database connection initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        logger.warning("⚠️ Continuing with development mode (database queries will fail)")
        engine = None
        SessionLocal = None
        # Don't raise - allow app to start without database in dev mode


def get_db() -> Session:
    """Get database session dependency for FastAPI."""
    if SessionLocal is None:
        logger.warning("⚠️ Database not initialized (SessionLocal is None)")
    
    if SessionLocal is None:
        # Return None session - CRUD functions will handle it
        yield None
        return
    
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
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

