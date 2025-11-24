import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import UploadFile, HTTPException
import io
import zipfile
from .models.schemas import TaskStatus
from .logging import CustomLogger

class TaskManager:
    """Менеджер для управления асинхронными задачами"""
    
    _instance = None
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
        return cls._instance
    
    def create_task(self, white_bg: bool, files: List[UploadFile]) -> str:
        """Создает новую задачу и возвращает её ID"""
        task_id = str(uuid.uuid4())
        
        self._tasks[task_id] = {
            "status": TaskStatus.PENDING,
            "white_bg": white_bg,
            "files": files,
            "progress": 0,
            "processed_files": 0,
            "total_files": len(files),
            "start_time": datetime.now(),
            "end_time": None,
            "result": None,
            "error": None,
            "logger": None
        }
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о задаче"""
        return self._tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        """Обновляет статус задачи"""
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status
            for key, value in kwargs.items():
                if key in self._tasks[task_id]:
                    self._tasks[task_id][key] = value
    
    def set_task_result(self, task_id: str, zip_buffer: io.BytesIO):
        """Сохраняет результат задачи"""
        if task_id in self._tasks:
            self._tasks[task_id]["result"] = zip_buffer
            self._tasks[task_id]["end_time"] = datetime.now()
    
    def set_task_error(self, task_id: str, error: str):
        """Сохраняет ошибку задачи"""
        if task_id in self._tasks:
            self._tasks[task_id]["error"] = error
            self._tasks[task_id]["status"] = TaskStatus.FAILED
            self._tasks[task_id]["end_time"] = datetime.now()
    
    def remove_task(self, task_id: str):
        """Удаляет задачу по id"""
        self._tasks.pop(task_id, None)

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Очищает старые задачи для экономии памяти"""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task_info in self._tasks.items():
            if task_info["end_time"] and (current_time - task_info["end_time"]).total_seconds() > max_age_hours * 3600:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()