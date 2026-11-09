import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models import User
from app.schemas.user import UserCreate


def reset_password(email: str, password: str, session_factory=SessionLocal):
    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            raise ValueError("User not found")
        UserCreate(username=user.username, email=user.email, password=password)
        user.hashed_password = hash_password(password)
        user.token_version += 1
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restablecer una contraseña local con acceso administrativo a la base de datos")
    parser.add_argument("email")
    arguments = parser.parse_args()
    first = getpass("Nueva contraseña: ")
    second = getpass("Confirmación: ")
    if first != second:
        raise SystemExit("Las contraseñas no coinciden.")
    reset_password(arguments.email, first)
    print("Contraseña actualizada con Argon2 y sesiones anteriores revocadas.")
