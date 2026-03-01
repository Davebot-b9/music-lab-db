from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app.schemas.user import LoginRequest, Token, UserResponse, ProfileUpdate, ChangePasswordRequest
from app.crud.crud_user import authenticate_user, verify_password, get_password_hash
from app.core.security import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_DAYS
from app.models.user import User

router = APIRouter()

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    return Token(access_token=access_token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update display_name and/or avatar_url for the current user."""
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip() or None
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url or None
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change the current user's password after verifying the current one."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta."
        )
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe tener al menos 6 caracteres."
        )
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Contraseña actualizada correctamente."}
