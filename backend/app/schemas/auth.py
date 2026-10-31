from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        normalised = value.strip().lower()
        if not EMAIL_PATTERN.match(normalised):
            raise ValueError("Enter a valid email address")
        return normalised


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    id: int
    email: str | None
    display_name: str
    is_guest: bool


class SessionOut(BaseModel):
    user: UserOut | None
    csrf_token: str | None
