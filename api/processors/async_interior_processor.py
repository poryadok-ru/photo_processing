import io
from typing import List, Tuple
from fastapi import UploadFile
import asyncio
from PIL import Image

from .async_base import AsyncBaseProcessor
from interior.async_ai_client import AsyncAIClient
from interior.config import Config
from ..logging import CustomLogger

class AsyncInteriorProcessor(AsyncBaseProcessor):
    """Асинхронный обработчик для интерьеров"""
    
    def __init__(self):
        super().__init__("interior")
        self.ai_client = AsyncAIClient()
    
    async def process_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Обрабатывает одно изображение для интерьера"""
        logger = CustomLogger("interior")
        
        try:
            logger.info(f"Начало обработки интерьера: {file.filename}")
            
            # Читаем файл
            image_data = await self.save_uploaded_file(file)
            
            # Анализируем категорию
            async with self.semaphore:
                main_category, subcategory = await self.ai_client.analyze_thematic_subcategory(
                    image_data, logger
                )
            
            logger.info(f"Категория для {file.filename}: {main_category} - {subcategory}")
            
            # Генерируем промпт
            prompt = self._generate_context_prompt(main_category, subcategory)
            
            # Генерируем изображение
            async with self.semaphore:
                processed_data = await self.ai_client.edit_image_with_gemini(
                    image_data, prompt, logger
                )
            
            if not processed_data:
                raise Exception("Image generation failed")
            
            # Обрезаем до 3:4 (синхронно, но быстро)
            processed_image = Image.open(io.BytesIO(processed_data))
            cropped_image = self._crop_to_3_4(processed_image)
            
            # Сохраняем в bytes
            output_buffer = io.BytesIO()
            cropped_image.save(output_buffer, format="JPEG", quality=95)
            processed_data = output_buffer.getvalue()
            
            output_filename = f"{file.filename.split('.')[0]}_in_{main_category.lower()}.jpg"
            logger.info(f"Успешно обработан: {file.filename}")
            logger.finish_success(
                filename=file.filename,
                category=main_category,
                subcategory=subcategory
            )
            
            return processed_data, output_filename
            
        except Exception as e:
            logger.error(f"Ошибка при обработке {file.filename}: {e}")
            logger.finish_error(error=str(e))
            raise
    
    def _generate_context_prompt(self, main_category: str, subcategory: str) -> str:
        """Генерирует промпт для обработки изображения"""
        categories = Config.get_thematic_categories()
        description = categories.get(main_category, {}).get(subcategory, "")
        
        return f"Обработай изображение товара категории {main_category}, подкатегории {subcategory}. {description}. Создай профессиональное изображение для маркетплейса."
    
    def _crop_to_3_4(self, image: Image.Image) -> Image.Image:
        """Обрезает изображение до 3:4 (синхронно)"""
        width, height = image.size
        target_ratio = 3/4
        
        if width / height > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            return image.crop((left, 0, left + new_width, height))
        else:
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            return image.crop((0, top, width, top + new_height))
    
    async def process_batch(self, files: List[UploadFile]) -> io.BytesIO:
        """Обрабатывает батч файлов для интерьеров"""
        # Аналогично AsyncWhiteProcessor
        logger = CustomLogger("interior")
        
        try:
            logger.info(f"Начало пакетной обработки {len(files)} файлов")
            
            tasks = [self.process_single(file) for file in files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
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