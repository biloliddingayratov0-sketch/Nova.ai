from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginSchema, RegisterSchema, TokenSchema
from app.schemas.user import ChangePasswordSchema, UpdateProfileSchema, UserResponse
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.email == data.email, User.username == data.username)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email or username already exists",
        )

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenSchema)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    data: UpdateProfileSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.username and data.username != current_user.username:
        conflict = db.query(User).filter(User.username == data.username).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Username already taken")
        current_user.username = data.username

    if data.full_name is not None:
        current_user.full_name = data.full_name

    if data.bio is not None:
        current_user.bio = data.bio

    if data.avatar_color is not None:
        current_user.avatar_color = data.avatar_color

    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=200)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.delete(current_user)
    db.commit()
    return {"success": True, "message": "Account deleted successfully"}


@router.post("/change-password", status_code=200)
def change_password(
    data: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"success": True, "message": "Password changed successfully"}
