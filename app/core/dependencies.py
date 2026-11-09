import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.database import get_db
from app.models.user import User


security = HTTPBearer(auto_error=False)


def user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_access_token(token)
        user = db.get(User, int(payload["sub"]))
        if not user or not user.is_active or payload["type"] != "access" or payload["ver"] != user.token_version:
            raise jwt.InvalidTokenError()
        return user
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return user_from_token(credentials.credentials, db)
