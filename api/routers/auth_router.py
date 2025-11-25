"""
Роутер для аутентификации
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from api.services.auth_service import AuthService
from api.dependencies import verify_user, verify_admin, get_auth_service
from api.models.auth_schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user: dict = Depends(verify_user)
):
    """Получить текущего пользователя"""
    return UserResponse(**user)

