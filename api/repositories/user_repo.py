"""
Репозиторий для работы с пользователями
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from database.models import User
from database.db_session import get_db


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    def get_by_id(user_id: UUID) -> Optional[User]:
        """Получить пользователя по ID"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.expunge(user)
            return user
    
    @staticmethod
    def get_by_username(username: str) -> Optional[User]:
        """Получить пользователя по username"""
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if user:
                db.expunge(user)
            return user
    
    @staticmethod
    def get_all() -> List[User]:
        """Получить всех пользователей"""
        with get_db() as db:
            users = db.query(User).all()
            for user in users:
                db.expunge(user)
            return users
    
    @staticmethod
    def create(username: str, is_admin: bool = False, rate_limit: int = 100) -> User:
        """Создать нового пользователя"""
        with get_db() as db:
            user = User(
                username=username,
                is_admin=is_admin,
                rate_limit=rate_limit,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user
    
    @staticmethod
    def update(user_id: UUID, **kwargs) -> Optional[User]:
        """Обновить пользователя"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user
    
    @staticmethod
    def update_last_used(user_id: UUID) -> None:
        """Обновить время последнего использования"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_used = datetime.now(timezone.utc)
                db.commit()
    
    @staticmethod
    def delete(user_id: UUID) -> bool:
        """Удалить пользователя"""
        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            db.delete(user)
            db.commit()
            return True

