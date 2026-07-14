import pytest
from app.utils.security import hash_password, verify_password

def test_password_hashing_and_verification():
    raw_pw = "mysecretpassword123"
    hashed = hash_password(raw_pw)
    assert hashed != raw_pw
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_user_registration_and_login(auth_service):
    user, error = auth_service.register_user(
        full_name="Varsha Sharma",
        username="varsha",
        email="varsha@example.com",
        password="securepassword"
    )
    assert error is None
    assert user is not None
    assert user.username == "varsha"
    assert user.full_name == "Varsha Sharma"

    # Test login with username
    auth_user, err = auth_service.authenticate_user("varsha", "securepassword")
    assert err is None
    assert auth_user.id == user.id

    # Test login with email
    auth_user_email, err2 = auth_service.authenticate_user("varsha@example.com", "securepassword")
    assert err2 is None
    assert auth_user_email.id == user.id

    # Test personalized greeting
    greeting = auth_service.get_personalized_greeting(auth_user)
    assert "Varsha" in greeting

def test_duplicate_registration_fails(auth_service):
    auth_service.register_user("User One", "user1", "user1@example.com", "pass1234")
    dup_user, error = auth_service.register_user("User Two", "user1", "user2@example.com", "pass1234")
    assert dup_user is None
    assert "already taken" in error
