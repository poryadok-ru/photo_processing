"""
Сервис для работы с задачами
"""
from typing import Optional
from uuid import UUID
import io
from api.repositories import TaskRepository
from database.models import Task


class TaskService:
    """Сервис для работы с задачами"""
    
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo
    
    def create_task(self, white_bg: bool, total_files: int) -> dict:
        """Создать новую задачу"""
        task = self.task_repo.create(white_bg=white_bg, total_files=total_files)
        return self._task_to_dict(task)
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """Получить задачу"""
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return None
        
        return self._task_to_dict(task)
    
    def update_task_status(self, task_id: str, status: str, **kwargs) -> Optional[dict]:
        """Обновить статус задачи"""
        task = self.task_repo.update(task_id, status=status, **kwargs)
        return self._task_to_dict(task) if task else None
    
    def set_task_result(self, task_id: str, zip_buffer: io.BytesIO) -> Optional[dict]:
        """Установить результат задачи"""
        task = self.task_repo.set_result(task_id, zip_buffer.getvalue())
        return self._task_to_dict(task) if task else None
    
    def set_task_error(self, task_id: str, error: str) -> Optional[dict]:
        """Установить ошибку задачи"""
        task = self.task_repo.set_error(task_id, error)
        return self._task_to_dict(task) if task else None
    
    def delete_task(self, task_id: str) -> bool:
        """Удалить задачу"""
        return self.task_repo.delete(task_id)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Очистить старые задачи"""
        return self.task_repo.cleanup_old(max_age_hours)
    
    def _task_to_dict(self, task: Task) -> dict:
        """Преобразовать задачу в словарь"""
        result = task.to_dict()
        result["task_id"] = task.id
        
        if task.result_data:
            result["result"] = io.BytesIO(task.result_data)
        
        return result
