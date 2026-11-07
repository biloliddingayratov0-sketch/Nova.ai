from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = ""
    bio: Optional[str] = ""
    avatar_color: Optional[str] = "#9c7cff"
    role: str = "user"
    credits: int = 50
    plan: str = "free"
    plan_expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileSchema(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_color: Optional[str] = Field(None, max_length=20)


class ChangePasswordSchema(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
