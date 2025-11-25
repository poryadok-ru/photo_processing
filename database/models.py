"""
SQLAlchemy модели для БД
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class User(Base):
    """Модель пользователя с UUID аутентификацией"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    rate_limit = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used = Column(DateTime, nullable=True)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "id": str(self.id),
            "username": self.username,
            "is_admin": self.is_admin,
            "rate_limit": self.rate_limit,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class Task(Base):
    """Модель задачи"""
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    white_bg = Column(Boolean, default=True, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    processed_files = Column(Integer, default=0, nullable=False)
    total_files = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True, index=True)
    error = Column(Text, nullable=True)
    result_data = Column(LargeBinary, nullable=True)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "status": self.status,
            "white_bg": self.white_bg,
            "progress": self.progress,
            "processed_files": self.processed_files,
            "total_files": self.total_files,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "result": None 
        }


class ThematicCategory(Base):
    """Модель тематических категорий"""
    __tablename__ = "thematic_categories"
    
    main_category = Column(String(50), primary_key=True)
    subcategory = Column(String(50), primary_key=True)
    description = Column(Text, nullable=False)
    
    def to_dict(self) -> dict:
        """Преобразует в словарь"""
        return {
            "main_category": self.main_category,
            "subcategory": self.subcategory,
            "description": self.description
        }

