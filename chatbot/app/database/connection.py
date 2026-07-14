import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Configure engine arguments depending on DB dialect
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Dependency / context generator that yields a database session and closes it cleanly upon exit.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """
    Initialize all SQLAlchemy database tables if they do not already exist.
    Also imports models so they are registered with Base.metadata before create_all().
    """
    import app.models  # noqa: F401
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully initialized database tables.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise
