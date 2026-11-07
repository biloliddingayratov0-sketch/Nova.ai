from pydantic import BaseModel, EmailStr, Field


class RegisterSchema(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
