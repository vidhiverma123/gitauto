import random
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from app.utils.logger import log_event
from app.models.user import User

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register_user(self, full_name: str, username: str, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Registers a new user securely with bcrypt password hashing.
        Returns (user_object, error_message).
        """
        if not full_name.strip() or not username.strip() or not email.strip() or not password.strip():
            return None, "All fields are required."

        if self.user_repo.get_by_username(username.strip()):
            return None, f"Username '{username}' is already taken."

        if self.user_repo.get_by_email(email.strip()):
            return None, f"Email '{email}' is already registered."

        try:
            hashed_pw = hash_password(password)
            user = self.user_repo.create(
                full_name=full_name.strip(),
                username=username.strip(),
                email=email.strip(),
                hashed_password=hashed_pw
            )
            log_event(self.db, "USER_REGISTER", f"New user registered: {user.username}", user_id=user.id)
            return user, None
        except Exception as e:
            log_event(self.db, "AUTH_FAILURE", f"Registration exception: {e}")
            return None, f"Failed to register user due to a system error: {str(e)}"

    def authenticate_user(self, username_or_email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticates a user by checking username/email and verifying the bcrypt hash.
        """
        clean_identifier = username_or_email.strip()
        user = self.user_repo.get_by_username(clean_identifier)
        if not user:
            user = self.user_repo.get_by_email(clean_identifier)

        if not user or not verify_password(password, user.hashed_password):
            log_event(self.db, "LOGIN_FAILED", f"Failed login attempt for identifier: {clean_identifier}", user_id=user.id if user else None)
            return None, "Invalid username/email or password."

        # Update last login timestamp
        self.user_repo.update_last_login(user.id)
        log_event(self.db, "USER_LOGIN", f"User logged in successfully: {user.username}", user_id=user.id)
        return user, None

    def login_for_token(self, username_or_email: str, password: str) -> Tuple[Optional[str], Optional[User], Optional[str]]:
        """
        Authenticates and generates a JWT access token.
        Returns (access_token, user_object, error_message).
        """
        user, error = self.authenticate_user(username_or_email, password)
        if error or not user:
            return None, None, error

        token = create_access_token({"sub": user.id, "username": user.username})
        return token, user, None

    def get_user_from_token(self, token: str) -> Optional[User]:
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return None
        return self.user_repo.get_by_id(payload["sub"])

    def get_personalized_greeting(self, user: User) -> str:
        """
        Returns a friendly personalized greeting using the user's first name.
        Never asks for their name again after registration.
        """
        first_name = user.full_name.split()[0] if user.full_name else user.username
        greetings = [
            f"Welcome back, {first_name}!",
            f"Hi {first_name}! What would you like to work on today?",
            f"Hello {first_name}! Ready to explore ideas or solve problems today?"
        ]
        return random.choice(greetings)
