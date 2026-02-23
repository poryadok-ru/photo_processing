"""
Роутер для обработки изображений
"""
from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File
from fastapi.responses import Response
from typing import List
import threading
from api.services.task_service import TaskService
from api.dependencies import verify_user, get_task_service
from api.models.schemas import ProcessingResponse, TaskStatusResponse

router = APIRouter(prefix="/api/v1", tags=["processing"])

# ── Счётчик вариантов для generate_image ──────────────────────────────────
# Потокобезопасный: каждый запрос получает следующий вариант по кругу (1 → 2 → 1 → 2 …)
_variant_lock = threading.Lock()
_variant_counter = 0  # глобальный счётчик вызовов


def _next_variant() -> int:
    """Возвращает 1 или 2, чередуя при каждом вызове."""
    global _variant_counter
    with _variant_lock:
        _variant_counter += 1
        return 1 if _variant_counter % 2 == 1 else 2
# ─────────────────────────────────────────────────────────────────────────


@router.post("/processing/parallel", response_model=ProcessingResponse)
async def process_parallel(
    background_tasks: BackgroundTasks,
    white_bg: bool = True,
    files: List[UploadFile] = File(...),
    user: dict = Depends(verify_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Запуск параллельной обработки с возвратом идентификатора задачи"""
    from api.handlers.processing_handler import ProcessingHandler
    
    handler = ProcessingHandler(task_service=task_service)
    return await handler.process_parallel(
        background_tasks=background_tasks,
        white_bg=white_bg,
        files=files
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user: dict = Depends(verify_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Получить статус задачи"""
    from api.handlers.task_handler import TaskHandler
    
    handler = TaskHandler(task_service=task_service)
    return await handler.get_task_status(task_id, user)


@router.get("/tasks/{task_id}/download")
async def download_task_result(
    task_id: str,
    user: dict = Depends(verify_user),
    task_service: TaskService = Depends(get_task_service)
):
    """Скачать результат задачи"""
    from api.handlers.task_handler import TaskHandler
    
    handler = TaskHandler(task_service=task_service)
    result = await handler.download_task_result(task_id, user)
    
    task_service.delete_task(task_id)

    return Response(
        content=result.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=processed_{task_id}.zip",
        }
    )


@router.post("/processing/remove_background")
async def remove_background(
    file: UploadFile = File(...),
    user: dict = Depends(verify_user)
):
    """Удаляет фон с одного изображения"""
    from api.processors.async_white_processor import AsyncWhiteProcessor
    
    processor = AsyncWhiteProcessor()
    processed_data, output_filename = await processor.process_single(file)
    
    return Response(
        content=processed_data,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={output_filename}",
        }
    )


@router.post("/processing/generate_image")
async def generate_image(
    file: UploadFile = File(...),
    user: dict = Depends(verify_user)
):
    """
    Генерирует интерьерное фото товара.
    При каждом обращении чередует стиль интерьера:
      нечётный вызов  → variant 1 (светлый, скандинавский)
      чётный вызов    → variant 2 (тёмный, насыщенный)
    Возвращает одно изображение (image/jpeg).
    """
    from api.processors.async_interior_processor import AsyncInteriorProcessor

    variant = _next_variant()

    processor = AsyncInteriorProcessor()
    processed_data, output_filename = await processor.process_single(file, variant=variant)

    return Response(
        content=processed_data,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"attachment; filename={output_filename}",
            "X-Variant": str(variant),  # удобно для отладки
        }
    )