from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Maximum overflow connections
    echo=False,  # Set to True for SQL query logging (useful for debugging)
)

# Create SessionLocal class for database sessions
# SQLAlchemy 2.0: autocommit and autoflush are deprecated, use autocommit=False explicitly
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base class for declarative models (SQLAlchemy 2.0 syntax)
class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency function for getting database session.
    
    Usage:
        @router.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    # Import all models to register them with Base
    from app.db.models import Company, User, Employee  # noqa: F401
    Base.metadata.create_all(bind=engine)

