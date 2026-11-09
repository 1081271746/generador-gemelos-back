from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.security import hash_password, verify_password, password_hasher
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserUpdate, PasswordChange


def persist_user(db: Session, user: User) -> User:
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DomainError("Username or email already exists", 409)
    return user


def create_user(db: Session, user_data: UserCreate) -> User:
    user = User(username=user_data.username, email=str(user_data.email).lower(),
        hashed_password=hash_password(user_data.password))
    return persist_user(db, user)


def authenticate_user(db: Session, user_data: UserLogin) -> User | None:
    user = db.scalar(select(User).where(User.email == str(user_data.email).lower()))
    if user is None or not verify_password(user_data.password, user.hashed_password) or not user.is_active:
        return None
    if password_hasher.check_needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(user_data.password)
        db.commit()
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    user.username = data.username
    user.email = str(data.email).lower()
    return persist_user(db, user)


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise DomainError("Current password is incorrect", 400)
    user.hashed_password = hash_password(data.new_password)
    revoke_tokens(db, user)


def revoke_tokens(db: Session, user: User) -> None:
    user.token_version += 1
    db.commit()
