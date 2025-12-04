import io
from typing import List, Tuple
from fastapi import UploadFile
import asyncio

from .async_base import AsyncBaseProcessor
from white.async_pixian_client import AsyncPixianClient
from ..logging import CustomLogger

class AsyncWhiteProcessor(AsyncBaseProcessor):
    """Асинхронный обработчик для белого фона"""
    
    def __init__(self):
        super().__init__("white")
        self.pixian_client = AsyncPixianClient()
    
    async def process_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Обрабатывает одно изображение"""
        logger = CustomLogger("white")
        processing_type_name = "white_background"

        try:
            logger.info(f"Начало обработки белого фона: {file.filename}")
            
            # Читаем файл
            image_data = await self.save_uploaded_file(file)
            
            # Обрабатываем с ограничением параллелизма
            async with self.semaphore:
                success, processed_data, error_msg = await self.pixian_client.remove_background(
                    image_data, logger
                )
            
            if not success:
                logger.error(f"Ошибка обработки {file.filename}: {error_msg}")
                raise Exception(f"Processing failed: {error_msg}")
            
            output_filename = f"{file.filename.split('.')[0]}_white_test.png"
            logger.info(f"{processing_type_name} | Успешно обработан: {file.filename}")
            logger.finish_success(
                filename=file.filename,
                processing_type=processing_type_name,
                processed_filename=output_filename

            )
            
            return processed_data, output_filename
            
        except Exception as e:
            logger.error(f"{processing_type_name} | Ошибка при обработке {file.filename}: {e}")
            logger.finish_error(
                processing_type=processing_type_name,
                error=str(e)
            )
            raise
    
    async def process_batch(self, files: List[UploadFile]) -> io.BytesIO:
        """Обрабатывает батч файлов"""
        logger = CustomLogger("white")
        
        try:
            logger.info(f"Начало пакетной обработки {len(files)} файлов")
            
            # Создаем задачи для параллельной обработки
            tasks = [self.process_single(file) for file in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем успешные результаты
            successful_results = []
            error_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Ошибка обработки {files[i].filename}: {result}")
                else:
                    processed_data, filename = result
                    successful_results.append((filename, processed_data))
            
            if not successful_results:
                logger.finish_error(error="All processing failed")
                raise Exception("All images failed to process")
            
            # Создаем ZIP архив
            zip_buffer = await self.create_zip_response(successful_results)
            
            logger.info(f"Пакетная обработка завершена. Успешно: {len(successful_results)}, Ошибок: {error_count}")
            logger.finish_success(
                processed_count=len(successful_results),
                error_count=error_count,
                total_files=len(files)
            )
            
            return zip_buffer
            
        except Exception as e:
            logger.error(f"Ошибка пакетной обработки: {e}")
            logger.finish_error(error=str(e))
            raise