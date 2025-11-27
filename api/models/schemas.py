from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingResponse(BaseModel):
    task_id: str = Field(..., description="ID задачи для отслеживания статуса")

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: Optional[int] = 0  # 0-100%
    processed_files: Optional[int] = 0
    total_files: Optional[int] = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

class ImageResponse(BaseModel):
    filename: str
    size: int
    message: str