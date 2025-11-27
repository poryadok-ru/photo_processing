from pydantic import BaseModel, validator, Field
from typing import Optional
from uuid import UUID


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=255, description="Имя пользователя")
    is_admin: bool = Field(default=False, description="Является ли администратором")
    rate_limit: int = Field(default=100, ge=1, le=10000, description="Лимит запросов в минуту")
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()


class UserResponse(BaseModel):
    id: str = Field(..., description="UUID пользователя")
    username: str = Field(..., description="Имя пользователя")
    is_admin: bool = Field(..., description="Является ли администратором")
    created_at: Optional[str] = Field(None, description="Дата создания")
    last_used: Optional[str] = Field(None, description="Последнее использование")
    rate_limit: int = Field(..., ge=1, le=10000, description="Лимит запросов")
    is_active: bool = Field(..., description="Активен ли пользователь")


class UserUpdate(BaseModel):
    is_admin: Optional[bool] = Field(None, description="Является ли администратором")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="Лимит запросов в минуту")
    is_active: Optional[bool] = Field(None, description="Активен ли пользователь")