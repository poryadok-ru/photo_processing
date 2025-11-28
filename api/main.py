from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import asyncio
import logging

from core.config import config
from api.services.task_service import TaskService
from api.repositories import TaskRepository
from database.db_session import get_db
from api.routers import auth_router, admin_router, processing_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Image Processing API",
    description="API для обработки изображений",
    version="3.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/photo_processing"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(processing_router)


@app.on_event("startup")
async def startup_event():
    """Запускаем периодическую очистку старых задач"""
    logger.info("Starting application...")
    asyncio.create_task(periodic_cleanup())


async def periodic_cleanup():
    """Периодическая очистка старых задач"""
    task_repo = TaskRepository()
    task_service = TaskService(task_repo=task_repo)
    
    while True:
        await asyncio.sleep(config.app.task_cleanup_interval_hours * 3600)
        try:
            deleted = task_service.cleanup_old_tasks(config.app.task_max_age_hours)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old tasks")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@app.get("/health", tags=["sys"])
async def health_check():
    """Health check endpoint с проверкой БД"""
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
