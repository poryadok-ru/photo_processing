"""
Handlers для аутентификации и управления пользователями
"""
from typing import List
from uuid import UUID
from fastapi import HTTPException, Depends
from api.services.auth_service import AuthService
from api.dependencies import verify_user, verify_admin, get_auth_service
from api.models.auth_schemas import UserCreate, UserResponse, UserUpdate


class AuthHandler:
    """Handler для работы с аутентификацией"""
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    async def get_current_user(self, user: dict = Depends(verify_user)) -> UserResponse:
        """Получить текущего пользователя"""
        return UserResponse(**user)
    
    async def create_user(
        self,
        user_data: UserCreate,
        current_user: dict = Depends(verify_admin)
    ) -> UserResponse:
        """Создать нового пользователя (только для админов)"""
        try:
            user = self.auth_service.create_user(
                username=user_data.username,
                is_admin=user_data.is_admin,
                rate_limit=user_data.rate_limit
            )
            return UserResponse(**user)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_users(
        self,
        current_user: dict = Depends(verify_admin)
    ) -> List[UserResponse]:
        """Получить список всех пользователей (только для админов)"""
        users = self.auth_service.get_all_users()
        return [UserResponse(**user) for user in users]
    
    async def get_user(
        self,
        user_id: UUID,
        current_user: dict = Depends(verify_admin)
    ) -> UserResponse:
        """Получить пользователя по ID (только для админов)"""
        user = self.auth_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(**user)
    
    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate,
        current_user: dict = Depends(verify_admin)
    ) -> UserResponse:
        """Обновить пользователя (только для админов)"""
        try:
            updates = user_data.model_dump(exclude_unset=True)
            user = self.auth_service.update_user(user_id, updates, current_user)
            return UserResponse(**user)
        except (ValueError, PermissionError) as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def delete_user(
        self,
        user_id: UUID,
        current_user: dict = Depends(verify_admin)
    ) -> dict:
        """Удалить пользователя (только для админов)"""
        try:
            success = self.auth_service.delete_user(user_id, current_user)
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            return {"message": "User deleted successfully"}
        except (ValueError, PermissionError) as e:
            raise HTTPException(status_code=400, detail=str(e))

