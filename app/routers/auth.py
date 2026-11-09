from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, UserUpdate, PasswordChange
from app.services.auth_service import create_user, authenticate_user, update_user, change_password, revoke_tokens


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, data)


@router.post("/login", response_model=Token)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, data)
    if user is None:
        raise HTTPException(401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token({"sub": str(user.id), "ver": user.token_version}))


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserResponse)
def edit_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_user(db, user, data)


@router.post("/password", status_code=204)
def update_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    change_password(db, user, data)
    return Response(status_code=204)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    revoke_tokens(db, user)
    return Response(status_code=204)
