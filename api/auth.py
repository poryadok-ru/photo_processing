import os
import json
import secrets
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import hashlib
import time

security = HTTPBearer()

if os.path.exists('/app'):
    USERS_FILE = Path('/app/data/users.json')
else:
    USERS_FILE = Path(__file__).parent.parent / 'data' / 'users.json'

USERS_FILE.parent.mkdir(exist_ok=True)

class AuthManager:
    """Менеджер аутентификации с хранением в JSON"""
    
    def __init__(self, users_file: Path = USERS_FILE):
        self.users_file = users_file
        self.users_file.parent.mkdir(exist_ok=True)
    
    def _load_users(self) -> Dict[str, Any]:
        """Загружает пользователей из JSON файла"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"users": []}
    
    def _save_users(self, data: Dict[str, Any]):
        """Сохраняет пользователей в JSON файл"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_api_key(self) -> str:
        """Генерирует случайный API ключ"""
        return secrets.token_urlsafe(32)
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Проверяет API ключ и возвращает данные пользователя"""
        data = self._load_users()
        
        for user in data.get("users", []):
            if user.get("api_key") == api_key and user.get("is_active", True):
                # Обновляем время последнего использования
                user["last_used"] = time.time()
                self._save_users(data)
                return user
        
        return None
    
    def create_user(self, username: str, is_admin: bool = False, rate_limit: int = 100) -> str:
        """Создает нового пользователя и возвращает API ключ"""
        data = self._load_users()
        
        # Проверяем, что username уникален
        for user in data.get("users", []):
            if user.get("username") == username:
                raise ValueError(f"Пользователь {username} уже существует")
        
        # Создаем нового пользователя
        api_key = self._generate_api_key()
        new_user = {
            "username": username,
            "api_key": api_key,
            "is_admin": is_admin,
            "created_at": time.time(),
            "last_used": None,
            "rate_limit": rate_limit,
            "is_active": True
        }
        
        data["users"].append(new_user)
        self._save_users(data)
        
        return api_key
    
    def delete_user(self, username: str, current_user: Dict[str, Any]) -> bool:
        """Удаляет пользователя (только для администраторов)"""
        if not current_user.get("is_admin"):
            raise PermissionError("Только администраторы могут удалять пользователей")
        
        # Не позволяем удалить себя
        if current_user.get("username") == username:
            raise ValueError("Нельзя удалить собственный аккаунт")
        
        data = self._load_users()
        initial_length = len(data.get("users", []))
        
        data["users"] = [user for user in data.get("users", []) 
                        if user.get("username") != username]
        
        if len(data["users"]) == initial_length:
            return False  # Пользователь не найден
        
        self._save_users(data)
        return True
    
    def get_users(self, current_user: Dict[str, Any]) -> list:
        """Возвращает список пользователей (только для администраторов)"""
        if not current_user.get("is_admin"):
            raise PermissionError("Только администраторы могут просматривать список пользователей")
        
        data = self._load_users()
        # Не возвращаем API ключи в списке
        return [
            {
                "username": user.get("username"),
                "is_admin": user.get("is_admin", False),
                "created_at": user.get("created_at"),
                "last_used": user.get("last_used"),
                "rate_limit": user.get("rate_limit", 100),
                "is_active": user.get("is_active", True)
            }
            for user in data.get("users", [])
        ]
    
    def update_user(self, username: str, updates: Dict[str, Any], current_user: Dict[str, Any]) -> bool:
        """Обновляет данные пользователя (только для администраторов)"""
        if not current_user.get("is_admin"):
            raise PermissionError("Только администраторы могут обновлять пользователей")
        
        data = self._load_users()
        user_found = False
        
        for user in data.get("users", []):
            if user.get("username") == username:
                # Не позволяем изменять API ключ через этот метод
                updates.pop("api_key", None)
                user.update(updates)
                user_found = True
                break
        
        if user_found:
            self._save_users(data)
        
        return user_found

    def regenerate_api_key(self, username: str, current_user: Dict[str, Any]) -> str:
        """Генерирует новый API ключ для пользователя"""
        if not current_user.get("is_admin") and current_user.get("username") != username:
            raise PermissionError("Можно обновлять только свой ключ")
        
        data = self._load_users()
        
        for user in data.get("users", []):
            if user.get("username") == username:
                new_api_key = self._generate_api_key()
                user["api_key"] = new_api_key
                self._save_users(data)
                return new_api_key
        
        raise ValueError(f"Пользователь {username} не найден")

# Глобальный экземпляр менеджера аутентификации
auth_manager = AuthManager()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Зависимость для проверки API ключа"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    user = auth_manager.verify_api_key(api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def verify_admin(user: Dict[str, Any] = Depends(verify_api_key)) -> Dict[str, Any]:
    """Зависимость для проверки прав администратора"""
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return user