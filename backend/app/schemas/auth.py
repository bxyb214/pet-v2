"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(LoginIn):
    invite_code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(default="", max_length=64)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    username: str
    display_name: str
    perms: str
    is_admin: bool
    exam: str = "pet"
    ai_enabled: bool = False


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    perms: str
    is_admin: bool
    exam: str = "pet"
    ai_enabled: bool = False

    model_config = {"from_attributes": True}


class ExamIn(BaseModel):
    exam: str = Field(pattern="^(pet|ket|fce|junior)$")
