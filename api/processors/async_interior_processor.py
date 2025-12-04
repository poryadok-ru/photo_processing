import io
from typing import List, Tuple
from fastapi import UploadFile
import asyncio
from PIL import Image

from .async_base import AsyncBaseProcessor
from interior.async_ai_client import AsyncAIClient
from interior.config import Config
from ..logging import CustomLogger
from interior.image_processor import ImageProcessor

class AsyncInteriorProcessor(AsyncBaseProcessor):
    """Асинхронный обработчик для интерьеров"""
    
    def __init__(self):
        super().__init__("interior")
        self.ai_client = AsyncAIClient()
    

    async def process_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Обрабатывает одно изображение для интерьера (с корректным препроцессингом!)"""
        logger = CustomLogger("interior")
        img_proc = ImageProcessor()  # СТАТИЧЕСКИЕ методы, можно не создавать экземпляр
        processing_type_name = "interior"
        try:
            logger.info(f"Начало обработки интерьера: {file.filename}")

            # Читаем файл как bytes
            image_data = await self.save_uploaded_file(file)  # Получаем bytes

            # 1. Открываем как PIL.Image
            with Image.open(io.BytesIO(image_data)) as img:
                # 2. Синхронно применяем orientation + форматирование в RGB
                orientation = img_proc.get_image_orientation(img)
                img = img_proc.apply_orientation(img, orientation)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 3. Форматируем в 3:4 c бордюрами (extend_with_border_color)
                width, height = img.size
                target_ratio = 3/4
                current_ratio = width / height
                if current_ratio > target_ratio:
                    new_width = width
                    new_height = int(width / target_ratio)
                else:
                    new_height = height
                    new_width = int(height * target_ratio)
                img_3_4 = img_proc.extend_with_border_color(img, new_width, new_height)

                # Переводим обратно в bytes для передачи в нейросеть
                buf_3_4 = io.BytesIO()
                img_3_4.save(buf_3_4, format="JPEG", quality=95)
                img_3_4_bytes = buf_3_4.getvalue()

            # 4. Анализируем категорию
            async with self.semaphore:
                main_category, subcategory = await self.ai_client.analyze_thematic_subcategory(
                    img_3_4_bytes, logger
                )
            logger.info(f"Категория для {file.filename}: {main_category} - {subcategory}")

            # 5. Генерируем промпт
            prompt = self._generate_context_prompt(main_category, subcategory)

            # 6. Генерируем изображение
            async with self.semaphore:
                processed_data = await self.ai_client.edit_image_with_gemini(
                    img_3_4_bytes, prompt, logger
                )
            if not processed_data:
                raise Exception("Image generation failed")

            # 7. Открываем результат -> crop_to_3_4
            processed_image = Image.open(io.BytesIO(processed_data))
            cropped_image = img_proc.crop_to_3_4(processed_image)

            output_buffer = io.BytesIO()
            cropped_image.save(output_buffer, format="JPEG", quality=95)
            processed_data = output_buffer.getvalue()

            output_filename = f"{file.filename.split('.')[0]}_in_{main_category.lower()}.jpg"
            logger.info(f"{processing_type_name} | Успешно обработан: {file.filename}")
            logger.finish_success(
                filename=file.filename,
                processing_type=processing_type_name,
                category=main_category,
                subcategory=subcategory
            )
            return processed_data, output_filename

        except Exception as e:
            logger.error(f"{processing_type_name} | Ошибка при обработке {file.filename}: {e}")
            logger.finish_error(
                processing_type=processing_type_name,
                error=str(e)
            )
            raise
    
    def _generate_context_prompt(self, main_category: str, subcategory: str) -> str:
        """Генерирует промпт для обработки изображения"""
        categories = Config.get_thematic_categories()
        description = categories.get(main_category, {}).get(subcategory, "")
        context = Config.THEMATIC_SUBCATEGORIES.get(main_category, {}).get(subcategory, "neutral interior setting")

        prompt = f"""
CREATE NATURAL PRODUCT PHOTO IN CONTEXT:

PRODUCT PRESERVATION:
- Use the EXACT same product from the input image
- Maintain the SAME angle, orientation, and position as in the original photo
- Do NOT change the product's perspective or viewing angle
- Preserve all product details, colors, textures exactly as shown
- Keep all text, labels, logos completely unchanged

CONTEXT AND SETTING:
- Place the product in a {main_category.lower()} environment: {context}
- The product should appear naturally placed in this setting
- Maintain the same scale and proportions as in the original

BACKGROUND AND COMPOSITION:
- Create a soft, slightly blurred background that matches {main_category} aesthetic
- Background should be authentic but not distracting from the product
- Use natural lighting that complements the product's original appearance
- Add subtle contextual elements that make sense for {subcategory.lower()}

STYLING GUIDELINES:
- The scene should look realistic and professionally styled
- Product must remain the main focus of the image
- Keep the composition clean and uncluttered
- Lighting should highlight the product naturally

TECHNICAL REQUIREMENTS:
- High-quality professional photography
- Product appearance must be identical to input (only environment changes)
- Maintain original product angle and orientation
- Soft background blur to keep focus on product

FINAL OUTPUT: Natural product photo in appropriate {main_category} context, with identical product presentation.
"""
        return prompt
    
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