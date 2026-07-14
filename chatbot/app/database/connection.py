import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Configure engine arguments depending on DB dialect.
# In SQLite, connect_args={"check_same_thread": False} was required to allow multiple threads to access the db file.
# For PostgreSQL, this is not needed and will cause an error if passed, so we use an empty dictionary.
# if settings.DATABASE_URL.startswith("sqlite"):
#     connect_args["check_same_thread"] = False
connect_args = {}

# Initialize the SQLAlchemy database engine.
# - settings.DATABASE_URL: connection string pointing to PostgreSQL
# - pool_pre_ping=True: test connections before executing queries to safely recycle dead connections (highly recommended for Postgres)
# - echo=False: set to True if you want to print all generated SQL queries to stdout for debugging
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
