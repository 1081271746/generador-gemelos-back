from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


def create_user(db: Session, user_data: UserCreate) -> User:
    existing_user = (
        db.query(User)
        .filter(
            (User.username == user_data.username)
            | (User.email == user_data.email)
        )
        .first()
    )

    if existing_user:
        raise ValueError("Username or email already exists.")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def authenticate_user(db: Session, user_data: UserLogin) -> User | None:
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user:
        return None

    if not verify_password(
        user_data.password,
        user.hashed_password,
    ):
        return None

    if not user.is_active:
        return None

    return user