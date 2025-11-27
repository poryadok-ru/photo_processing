"""
Роутер для административных операций
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from api.services.auth_service import AuthService
from api.dependencies import verify_admin, get_auth_service
from api.models.auth_schemas import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    admin: dict = Depends(verify_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Создание нового пользователя системы"""
    try:
        user = auth_service.create_user(
            username=user_data.username,
            is_admin=user_data.is_admin,
            rate_limit=user_data.rate_limit
        )
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    admin: dict = Depends(verify_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Получение списка всех пользователей системы"""
    users = auth_service.get_all_users()
    return [UserResponse(**user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: dict = Depends(verify_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Получить пользователя по ID"""
    user = auth_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    admin: dict = Depends(verify_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Обновление данных пользователя"""
    try:
        updates = user_data.model_dump(exclude_unset=True)
        user = auth_service.update_user(user_id, updates, admin)
        return UserResponse(**user)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: dict = Depends(verify_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Удаление пользователя из системы"""
    try:
        success = auth_service.delete_user(user_id, admin)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

