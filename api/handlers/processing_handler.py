"""
Handlers для обработки изображений
"""
from typing import List
from fastapi import UploadFile, HTTPException, BackgroundTasks
from core.config import config
from api.services.task_service import TaskService
from api.models.schemas import ProcessingResponse


class ProcessingHandler:
    """Handler для обработки изображений"""
    
    def __init__(self, task_service: TaskService):
        self.task_service = task_service
    
    async def validate_files(self, files: List[UploadFile]) -> List[UploadFile]:
        """Валидация файлов"""
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        if len(files) > config.app.max_files_count:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files. Maximum {config.app.max_files_count} files allowed"
            )
        
        validated_files = []
        for file in files:
            content = await file.read()
            await file.seek(0)
            
            if len(content) > config.app.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is too large. Maximum size is {config.app.max_file_size} bytes"
                )
            
            if file.content_type not in config.app.allowed_content_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} has unsupported content type. Allowed: {', '.join(config.app.allowed_content_types)}"
                )
            
            if len(content) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is empty"
                )
            
            validated_files.append(file)
        
        return validated_files
    
    async def process_parallel(
        self,
        background_tasks: BackgroundTasks,
        white_bg: bool,
        files: List[UploadFile]
    ) -> ProcessingResponse:
        """Запустить параллельную обработку"""
        from api.background_processor import BackgroundProcessor
        
        validated_files = await self.validate_files(files)
        
        task = self.task_service.create_task(
            white_bg=white_bg,
            total_files=len(validated_files)
        )
        
        processor = BackgroundProcessor(task_service=self.task_service)
        background_tasks.add_task(
            processor.process_task,
            task["task_id"],
            validated_files,
            white_bg
        )
        
        return ProcessingResponse(task_id=task["task_id"])
