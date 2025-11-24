from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import Response, StreamingResponse
from typing import List
import asyncio
from datetime import datetime
import io

import os
from pathlib import Path

from .task_manager import task_manager
from .background_processor import background_processor
from .processors.async_white_processor import AsyncWhiteProcessor
from .processors.async_interior_processor import AsyncInteriorProcessor
from .models.schemas import ProcessingResponse, ImageResponse, TaskStatusResponse, TaskStatus
from .auth import auth_manager, verify_api_key, verify_admin
from .models.auth_schemas import UserCreate, UserResponse, APIKeyResponse, UserUpdate

if os.path.exists('/app'):
    BASE_DIR = Path('/app')
else:
    BASE_DIR = Path(__file__).parent.parent

USERS_FILE = BASE_DIR / 'data' / 'users.json'
USERS_FILE.parent.mkdir(exist_ok=True)

app = FastAPI(
    title="Image Processing API",
    description="API для обработки изображений",
    version="2.3.0"
)

@app.on_event("startup")
async def startup_event():
    """Запускаем периодическую очистку старых задач"""
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    """Периодическая очистка старых задач"""
    while True:
        await asyncio.sleep(3600)
        task_manager.cleanup_old_tasks()

# ==================== CHECK HEALTH ====================

@app.get("/health", tags=["sys"])
async def health_check():
    return {"status": "healthy"}

# ==================== AUTH ENDPOINTS ====================

@app.get("/api/v1/tests/auth/me", tags=["auth"])
async def test_auth(user: dict = Depends(verify_api_key)):
    """Тестирование аутентификации и проверка прав пользователя"""
    return {
        "authenticated": True,
        "username": user.get("username"),
        "is_admin": user.get("is_admin", False)
    }

# ==================== PROCESSING ENDPOINTS ====================

@app.post("/api/v1/processing/parallel", 
          response_model=ProcessingResponse,
          tags=["processing"])
async def process_parallel(
    background_tasks: BackgroundTasks,
    white_bg: bool = True,
    files: List[UploadFile] = File(...),
    user: dict = Depends(verify_api_key)
):
    """
    Запуск параллельной обработки с возвратом идентификатора задачи
    """
    if not files:
        raise HTTPException(400, "No files provided")
    
    # Создаем задачу
    task_id = task_manager.create_task(white_bg, files)
    
    # Запускаем фоновую обработку
    background_tasks.add_task(background_processor.process_task, task_id)
    
    return ProcessingResponse(
        success=True,
        message="Parallel processing started",
        file_count=len(files),
        task_id=task_id
    )

# ==================== TASKS ENDPOINTS ====================

@app.get("/api/v1/tasks/{task_id}/status", 
         response_model=TaskStatusResponse,
         tags=["tasks"])
async def get_task_status(
    task_id: str,
    user: dict = Depends(verify_api_key)
):
    """Получение статуса и прогресса выполнения задачи"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        processed_files=task["processed_files"],
        total_files=task["total_files"],
        start_time=task["start_time"],
        end_time=task["end_time"],
        error=task["error"]
    )



@app.get("/api/v1/tasks/{task_id}/download", tags=["tasks"])
async def download_task_result(
    task_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_api_key)
):
    """Скачивание результатов выполненной задачи"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(400, "Task not completed yet")
    
    if not task["result"]:
        raise HTTPException(500, "Task result not available")
    
    # Удалить задачу в фоне после возврата ответа
    background_tasks.add_task(task_manager.remove_task, task_id)
    
    zip_buffer: io.BytesIO = task["result"]

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=processed_{task_id}.zip",
        }
    )

# ==================== ADMIN ENDPOINTS ====================

@app.post("/api/v1/admin/users", 
          response_model=APIKeyResponse,
          tags=["admin"])
async def create_user(
    user_data: UserCreate,
    admin: dict = Depends(verify_admin)
):
    """Создание нового пользователя системы"""
    try:
        api_key = auth_manager.create_user(
            username=user_data.username,
            is_admin=user_data.is_admin,
            rate_limit=user_data.rate_limit
        )
        
        return APIKeyResponse(
            username=user_data.username,
            api_key=api_key,
            message="User created successfully"
        )
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to create user: {str(e)}")



@app.get("/api/v1/admin/users", 
         response_model=List[UserResponse],
         tags=["admin"])
async def list_users(admin: dict = Depends(verify_admin)):
    """Получение списка всех пользователей системы"""
    try:
        users = auth_manager.get_users(admin)
        return users
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to get users: {str(e)}")



@app.put("/api/v1/admin/users/{username}",
         tags=["admin"])
async def update_user(
    username: str,
    updates: UserUpdate,
    admin: dict = Depends(verify_admin)
):
    """Обновление данных пользователя"""
    try:
        success = auth_manager.update_user(username, updates.dict(exclude_unset=True), admin)
        if not success:
            raise HTTPException(404, f"User {username} not found")
        
        return {"message": f"User {username} updated successfully"}
        
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to update user: {str(e)}")



@app.delete("/api/v1/admin/users/{username}",
            tags=["admin"])
async def delete_user(
    username: str,
    admin: dict = Depends(verify_admin)
):
    """Удаление пользователя из системы"""
    try:
        success = auth_manager.delete_user(username, admin)
        if not success:
            raise HTTPException(404, f"User {username} not found")
        
        return {"message": f"User {username} deleted successfully"}
        
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to delete user: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)