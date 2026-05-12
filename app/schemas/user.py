import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)


def _validate_password(v: str) -> str:
    if not _PASSWORD_RE.match(v):
        raise ValueError(
            "Password must be at least 8 characters and contain at least one "
            "uppercase letter, lowercase letter, digit, and special character (@$!%*?&)."
        )
    return v


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
