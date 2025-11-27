"""
Зависимости для FastAPI (аутентификация, авторизация, сервисы)
"""
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status, Depends, Header
from api.services.auth_service import AuthService
from api.services.task_service import TaskService
from api.repositories import UserRepository, TaskRepository


def get_user_repository() -> UserRepository:
    """Получить репозиторий пользователей"""
    return UserRepository()


def get_task_repository() -> TaskRepository:
    """Получить репозиторий задач"""
    return TaskRepository()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """Получить сервис аутентификации"""
    return AuthService(user_repo=user_repo)


def get_task_service(
    task_repo: TaskRepository = Depends(get_task_repository)
) -> TaskService:
    """Получить сервис задач"""
    return TaskService(task_repo=task_repo)


async def verify_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Проверить пользователя по UUID из заголовка"""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.verify_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def verify_admin(
    user: dict = Depends(verify_user)
) -> dict:
    """Проверить права администратора"""
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return user

