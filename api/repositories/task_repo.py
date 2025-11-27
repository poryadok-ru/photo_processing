"""
Репозиторий для работы с задачами
"""
from typing import Optional, List
from uuid import UUID
import uuid
from datetime import datetime, timedelta, timezone
from database.models import Task
from database.db_session import get_db


class TaskRepository:
    """Репозиторий для работы с задачами"""
    
    @staticmethod
    def get_by_id(task_id: str) -> Optional[Task]:
        """Получить задачу по ID"""
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                db.expunge(task)
            return task
    
    @staticmethod
    def create(white_bg: bool, total_files: int) -> Task:
        """Создать новую задачу"""
        with get_db() as db:
            task = Task(
                id=str(uuid.uuid4()),
                white_bg=white_bg,
                total_files=total_files,
                status="pending",
                progress=0,
                processed_files=0,
                start_time=datetime.now(timezone.utc)
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            db.expunge(task)
            return task
    
    @staticmethod
    def update(task_id: str, **kwargs) -> Optional[Task]:
        """Обновить задачу"""
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            for key, value in kwargs.items():
                if hasattr(task, key) and key != "result_data":
                    setattr(task, key, value)
            
            db.commit()
            db.refresh(task)
            db.expunge(task)
            return task
    
    @staticmethod
    def set_result(task_id: str, result_data: bytes) -> Optional[Task]:
        """Установить результат задачи"""
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            task.result_data = result_data
            task.end_time = datetime.now(timezone.utc)
            db.commit()
            db.refresh(task)
            db.expunge(task)
            return task
    
    @staticmethod
    def set_error(task_id: str, error: str) -> Optional[Task]:
        """Установить ошибку задачи"""
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            task.error = error
            task.status = "failed"
            task.end_time = datetime.now(timezone.utc)
            db.commit()
            db.refresh(task)
            db.expunge(task)
            return task
    
    @staticmethod
    def delete(task_id: str) -> bool:
        """Удалить задачу"""
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            db.delete(task)
            db.commit()
            return True
    
    @staticmethod
    def cleanup_old(max_age_hours: int = 24) -> int:
        """Очистить старые задачи, возвращает количество удаленных"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with get_db() as db:
            old_tasks = db.query(Task).filter(
                Task.end_time.isnot(None),
                Task.end_time < cutoff_time
            ).all()
            
            count = len(old_tasks)
            for task in old_tasks:
                db.delete(task)
            db.commit()
            return count

