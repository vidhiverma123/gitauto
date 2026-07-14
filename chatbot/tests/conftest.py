import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.auth.service import AuthService
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.memory_repository import MemoryRepository

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh in-memory SQLite database session for each test function.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def auth_service(db_session):
    return AuthService(db_session)

@pytest.fixture(scope="function")
def user_repo(db_session):
    return UserRepository(db_session)

@pytest.fixture(scope="function")
def conv_repo(db_session):
    return ConversationRepository(db_session)

@pytest.fixture(scope="function")
def memory_repo(db_session):
    return MemoryRepository(db_session)
