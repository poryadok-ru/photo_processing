import io
import zipfile
from typing import List
from fastapi import UploadFile
from api.services.task_service import TaskService
from .processors.async_white_processor import AsyncWhiteProcessor
from .processors.async_interior_processor import AsyncInteriorProcessor
from .logging import CustomLogger


class BackgroundProcessor:
    """Обработчик фоновых задач"""
    
    def __init__(self, task_service: TaskService):
        self.task_service = task_service
    
    async def process_task(self, task_id: str, files: List[UploadFile], white_bg: bool):
        """Обрабатывает задачу в фоновом режиме"""
        task = self.task_service.get_task(task_id)
        if not task:
            return
        
        processing_type = "white" if white_bg else "interior"
        logger = CustomLogger(processing_type)
        self.task_service.update_task_status(task_id, "processing")
        
        try:
            logger.info(f"Начало фоновой обработки задачи {task_id}")
            logger.info(f"Файлов для обработки: {len(files)}")
            
            if white_bg:
                processor = AsyncWhiteProcessor()
            else:
                processor = AsyncInteriorProcessor()
            
            zip_buffer = await self._process_with_progress(processor, files, task_id, logger)
            
            self.task_service.set_task_result(task_id, zip_buffer)
            self.task_service.update_task_status(task_id, "completed", progress=100)
            
            logger.info(f"Фоновая обработка завершена успешно: {task_id}")
            
            processing_type_name = "white_background" if white_bg else "interior"
            logger.finish_success(
                processed_count=len(files),
                task_id=task_id,
                processing_type=processing_type_name,
                total_files=len(files)
            )
            
        except Exception as e:
            error_msg = f"Ошибка фоновой обработки: {str(e)}"
            logger.error(error_msg)
            self.task_service.set_task_error(task_id, error_msg)
            
            processing_type_name = "white_background" if white_bg else "interior"
            logger.finish_error(
                error=error_msg,
                task_id=task_id,
                processing_type=processing_type_name,
                total_files=len(files)
            )
    
    async def _process_with_progress(self, processor, files: List[UploadFile], task_id: str, logger: CustomLogger) -> io.BytesIO:
        """Обрабатывает файлы с обновлением прогресса"""
        total_files = len(files)
        processed_files = []
        
        for i, file in enumerate(files):
            try:
                progress = int((i / total_files) * 100)
                self.task_service.update_task_status(
                    task_id, 
                    "processing", 
                    progress=progress,
                    processed_files=i
                )
                
                logger.info(f"Обработка файла {i+1}/{total_files}: {file.filename}")
                
                result = await processor.process_single(file)

                # process_single всегда возвращает (bytes, filename)
                processed_data, filename = result
                processed_files.append((filename, processed_data))
                
                logger.debug(f"Успешно обработан: {file.filename}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки файла {file.filename}: {e}")
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, file_data in processed_files:
                zip_file.writestr(filename, file_data)
        
        zip_buffer.seek(0)
        return zip_buffer