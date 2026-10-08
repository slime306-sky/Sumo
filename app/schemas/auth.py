from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["creator", "brand"]


class RegisterRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Role


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user_id: int
    role: Role
    access_token: str
    token_type: Literal["bearer"] = "bearer"
