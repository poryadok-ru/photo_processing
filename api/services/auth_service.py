"""
Сервис аутентификации
"""
from typing import Optional
from uuid import UUID
from api.repositories import UserRepository
from database.models import User


class AuthService:
    """Сервис для работы с аутентификацией"""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def verify_user(self, user_id: UUID) -> Optional[dict]:
        """Проверить пользователя по UUID и вернуть данные"""
        user = self.user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        self.user_repo.update_last_used(user_id)
        
        return user.to_dict()
    
    def create_user(self, username: str, is_admin: bool = False, rate_limit: int = 100) -> dict:
        """Создать нового пользователя"""
        existing = self.user_repo.get_by_username(username)
        if existing:
            raise ValueError(f"Пользователь {username} уже существует")
        
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")
        if rate_limit < 1 or rate_limit > 10000:
            raise ValueError("Rate limit must be between 1 and 10000")
        
        user = self.user_repo.create(
            username=username.strip(),
            is_admin=is_admin,
            rate_limit=rate_limit
        )
        
        return user.to_dict()
    
    def get_user(self, user_id: UUID) -> Optional[dict]:
        """Получить пользователя"""
        user = self.user_repo.get_by_id(user_id)
        return user.to_dict() if user else None
    
    def get_all_users(self) -> list:
        """Получить всех пользователей"""
        users = self.user_repo.get_all()
        return [user.to_dict() for user in users]
    
    def update_user(self, user_id: UUID, updates: dict, current_user: dict) -> dict:
        """Обновить пользователя"""
        if not current_user.get("is_admin"):
            raise PermissionError("Только администраторы могут обновлять пользователей")
        
        if "rate_limit" in updates:
            if not isinstance(updates["rate_limit"], int) or updates["rate_limit"] < 1 or updates["rate_limit"] > 10000:
                raise ValueError("Rate limit must be between 1 and 10000")
        
        updates.pop("id", None)
        updates.pop("username", None)
        
        user = self.user_repo.update(user_id, **updates)
        if not user:
            raise ValueError("Пользователь не найден")
        
        return user.to_dict()
    
    def delete_user(self, user_id: UUID, current_user: dict) -> bool:
        """Удалить пользователя"""
        if not current_user.get("is_admin"):
            raise PermissionError("Только администраторы могут удалять пользователей")
        
        if current_user.get("id") == str(user_id):
            raise ValueError("Нельзя удалить собственный аккаунт")
        
        return self.user_repo.delete(user_id)

