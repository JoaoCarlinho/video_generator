"""Database connection management."""

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.config import settings
import logging
import ssl
import socket

logger = logging.getLogger(__name__)

# Monkey-patch socket.getaddrinfo to prefer IPv4
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Force IPv4 resolution for database connections."""
    try:
        # Try IPv4 first
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except socket.gaierror:
        # Fallback to original behavior if IPv4 fails
        return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _ipv4_preferred_getaddrinfo

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
            # Determine if this is a local or remote database
            # Treat VPC private IPs (10.0.x.x) as local since proxy doesn't handle SSL
            is_local = ('localhost' in db_url or '127.0.0.1' in db_url or
                       'postgres' in db_url or '10.0.' in db_url)
            
            # Remove any existing sslmode parameters first
            if 'sslmode=' in db_url:
                # Remove existing sslmode parameter
                parts = db_url.split('?')
                if len(parts) == 2:
                    base_url = parts[0]
                    params = parts[1].split('&')
                    params = [p for p in params if not p.startswith('sslmode=')]
                    if params:
                        db_url = base_url + '?' + '&'.join(params)
                    else:
                        db_url = base_url
            
            # Now add appropriate SSL mode
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
        
        # Configure connection arguments
        is_local = ('localhost' in db_url or '127.0.0.1' in db_url or
                   'postgres' in db_url or '10.0.' in db_url)

        connect_args = {
            'connect_timeout': 10,
            'options': '-c client_encoding=UTF8'
        }

        if is_local:
            connect_args['sslmode'] = 'disable'

        # VPC Lambda with IPv4: Use direct connection on port 5432
        # NAT Gateway provides IPv4-only networking
        logger.info("🔧 Using direct database connection (VPC provides IPv4)")

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

