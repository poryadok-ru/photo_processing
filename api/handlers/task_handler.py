"""
Handlers для работы с задачами
"""
from typing import Optional
from fastapi import HTTPException, Depends
from api.services.task_service import TaskService
from api.dependencies import verify_user
from api.models.schemas import TaskStatusResponse


class TaskHandler:
    """Handler для работы с задачами"""
    
    def __init__(self, task_service: TaskService):
        self.task_service = task_service
    
    async def get_task_status(self, task_id: str, user: dict = Depends(verify_user)) -> TaskStatusResponse:
        """Получить статус задачи"""
        task = self.task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            task_id=task["task_id"],
            status=task["status"],
            progress=task["progress"],
            processed_files=task["processed_files"],
            total_files=task["total_files"],
            error=task.get("error")
        )
    
    async def download_task_result(self, task_id: str, user: dict = Depends(verify_user)):
        """Скачать результат задачи"""
        task = self.task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task is not completed")
        
        if "result" not in task or task["result"] is None:
            raise HTTPException(status_code=404, detail="Task result not found")
        
        return task["result"]

