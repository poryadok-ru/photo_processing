import asyncio
import zipfile 
import io
from typing import List, Tuple, Optional, Callable
from fastapi import UploadFile
from ..logging import CustomLogger

class AsyncBaseProcessor:
    """Базовый асинхронный класс для обработчиков изображений"""
    
    def __init__(self, processing_type: str):
        self.processing_type = processing_type
        self.semaphore = asyncio.Semaphore(5)
        self.progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Устанавливает callback для отслеживания прогресса"""
        self.progress_callback = callback
    
    async def _update_progress(self, current: int, total: int):
        """Обновляет прогресс обработки"""
        if self.progress_callback:
            progress = int((current / total) * 100)
            await self.progress_callback(progress, current, total)
    
    async def save_uploaded_file(self, file: UploadFile) -> bytes:
        """Сохраняет загруженный файл в память"""
        content = await file.read()
        return content
    
    async def create_zip_response(self, processed_files: List[Tuple[str, bytes]]) -> io.BytesIO:
        """Создает zip-архив с обработанными файлами"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, file_data in processed_files:
                zip_file.writestr(filename, file_data)
        
        zip_buffer.seek(0)
        return zip_buffer
    
    async def process_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Обрабатывает одно изображение"""
        raise NotImplementedError("Subclasses must implement process_single")
    
    async def process_batch(self, files: List[UploadFile]) -> io.BytesIO:
        """Обрабатывает батч файлов"""
        raise NotImplementedError("Subclasses must implement process_batch")