from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import Response, StreamingResponse
from typing import List
import asyncio
from datetime import datetime
import io

from .task_manager import task_manager
from .background_processor import background_processor
from .processors.async_white_processor import AsyncWhiteProcessor
from .processors.async_interior_processor import AsyncInteriorProcessor
from .models.schemas import ProcessingResponse, ImageResponse, TaskStatusResponse, TaskStatus
from .auth import auth_manager, verify_api_key, verify_admin
from .models.auth_schemas import UserCreate, UserResponse, APIKeyResponse, UserUpdate

app = FastAPI(
    title="Image Processing API",
    description="API для обработки изображений с аутентификацией",
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
'''
@app.post(
    "/api/v1/processing/single",
    response_model=ImageResponse,
    tags=["processing"]
)
async def process_single_image(
    white_bg: bool = True,
    file: UploadFile = File(...),
    user: dict = Depends(verify_api_key)
):
    """Обработка одного изображения с возвратом результата напрямую"""
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(400, "Invalid image format")
    
    try:
        if white_bg:
            processor = AsyncWhiteProcessor()
        else:
            processor = AsyncInteriorProcessor()
        
        processed_data, filename = await processor.process_single(file)
        
        return StreamingResponse(
            io.BytesIO(processed_data),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")

@app.post(
    "/api/v1/processing/batch",
    response_class=Response,
    tags=["processing"]
)
async def process_batch(
    white_bg: bool = True,
    files: List[UploadFile] = File(...),
    user: dict = Depends(verify_api_key)
):
    """Пакетная обработка нескольких изображений с возвратом ZIP архива"""
    if not files:
        raise HTTPException(400, "No files provided")
    
    try:
        if white_bg:
            processor = AsyncWhiteProcessor()
        else:
            processor = AsyncInteriorProcessor()
        
        zip_buffer = await processor.process_batch(files)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=processed_images.zip",
            }
        )
        
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")
'''
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

@app.get("/api/v1/tasks/{task_id}/download",
         tags=["tasks"])
async def download_task_result(
    task_id: str,
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
    
    # Возвращаем ZIP архив
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

# ==================== TOKENS ENDPOINTS ====================
'''
@app.post("/admin/tokens/{username}/regenerate",
          tags=["tokens"])
async def regenerate_api_key(
    username: str,
    admin: dict = Depends(verify_admin)
):
    """Перегенерация API ключа для пользователя"""
    try:
        new_api_key = auth_manager.regenerate_api_key(username, admin)
        
        return {
            "username": username,
            "new_api_key": new_api_key,
            "message": "API key regenerated successfully"
        }
        
    except (PermissionError, ValueError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to regenerate API key: {str(e)}")
'''
# ==================== STATISTICS ENDPOINTS ====================
'''
@app.get("/admin/statistics",
         tags=["statistics"])
async def get_stats(admin: dict = Depends(verify_admin)):
    """Получение статистики использования API"""
    try:
        stats = {
            "total_tasks": len(task_manager._tasks),
            "active_tasks": sum(1 for task in task_manager._tasks.values() 
                              if task.get("status") == TaskStatus.PROCESSING),
            "completed_tasks": sum(1 for task in task_manager._tasks.values() 
                                 if task.get("status") == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for task in task_manager._tasks.values() 
                              if task.get("status") == TaskStatus.FAILED),
            "total_users": len(auth_manager.get_users(admin)),
            "active_users": len([u for u in auth_manager.get_users(admin) 
                               if u.get("is_active", True)]),
            "admin_users": len([u for u in auth_manager.get_users(admin) 
                              if u.get("is_admin", False)])
        }
        return stats
    except Exception as e:
        raise HTTPException(500, f"Failed to get stats: {str(e)}")

@app.get("/admin/statistics/tasks",
         tags=["admin", "statistics"])
async def get_tasks_statistics(admin: dict = Depends(verify_admin)):
    """Детальная статистика по задачам"""
    try:
        tasks = task_manager._tasks
        recent_tasks = sorted(
            [task for task in tasks.values() if task.get("start_time")],
            key=lambda x: x["start_time"],
            reverse=True
        )[:10]  # Последние 10 задач
        
        return {
            "recent_tasks": [
                {
                    "task_id": task_id,
                    "status": task.get("status"),
                    "progress": task.get("progress", 0),
                    "processed_files": task.get("processed_files", 0),
                    "total_files": task.get("total_files", 0),
                    "start_time": task.get("start_time"),
                    "end_time": task.get("end_time")
                }
                for task_id, task in list(tasks.items())[-10:]  # Последние 10 по времени создания
            ]
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to get tasks statistics: {str(e)}")
'''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)