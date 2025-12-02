"""
Handlers для обработки изображений
"""
from typing import List, Tuple
from fastapi import UploadFile, HTTPException, BackgroundTasks
from core.config import config
from api.services.task_service import TaskService
from api.models.schemas import ProcessingResponse
from api.logging import CustomLogger


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
        files: List[UploadFile],
        user: dict
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
    
    async def remove_background_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Удаляет фон с одного изображения"""
        from white.async_pixian_client import AsyncPixianClient
        
        logger = CustomLogger("white")
        image_data = await file.read()
        await file.seek(0)
        
        try:
            logger.info(f"Начало удаления фона: {file.filename}")
            
            pixian_client = AsyncPixianClient()
            success, processed_data, error_msg = await pixian_client.remove_background(
                image_data, logger
            )
            
            if not success:
                logger.error(f"Ошибка удаления фона {file.filename}: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Background removal failed: {error_msg}")
            
            output_filename = f"{file.filename.split('.')[0]}_no_bg.png"
            logger.info(f"Успешно удалён фон: {file.filename}")
            logger.finish_success(
                filename=file.filename,
                processed_filename=output_filename
            )
            
            return processed_data, output_filename
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка при удалении фона {file.filename}: {e}")
            logger.finish_error(error=str(e))
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    async def generate_image_single(self, file: UploadFile) -> Tuple[bytes, str]:
        """Генерирует изображение из одного файла"""
        from interior.async_ai_client import AsyncAIClient
        
        logger = CustomLogger("interior")
        image_data = await file.read()
        await file.seek(0)
        
        try:
            logger.info(f"Начало генерации изображения: {file.filename}")
            
            # Простой промпт для генерации изображения
            prompt = """
CREATE NATURAL PRODUCT PHOTO IN CONTEXT:

PRODUCT PRESERVATION:
- Use the EXACT same product from the input image
- Maintain the SAME angle, orientation, and position as in the original photo
- Do NOT change the product's perspective or viewing angle
- Preserve all product details, colors, textures exactly as shown
- Keep all text, labels, logos completely unchanged

CONTEXT AND SETTING:
- Place the product in a natural, professional interior setting
- The product should appear naturally placed in this setting
- Maintain the same scale and proportions as in the original

BACKGROUND AND COMPOSITION:
- Create a soft, slightly blurred background
- Background should be authentic but not distracting from the product
- Use natural lighting that complements the product's original appearance

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

FINAL OUTPUT: Natural product photo in appropriate context, with identical product presentation.
"""
            
            ai_client = AsyncAIClient()
            processed_data = await ai_client.edit_image_with_gemini(
                image_data, prompt, logger
            )
            
            if not processed_data:
                logger.error(f"Генерация изображения не удалась для {file.filename}")
                raise HTTPException(status_code=500, detail="Image generation failed")
            
            output_filename = f"{file.filename.split('.')[0]}_generated.jpg"
            logger.info(f"Успешно сгенерировано изображение: {file.filename}")
            logger.finish_success(
                filename=file.filename,
                processed_filename=output_filename
            )
            
            return processed_data, output_filename
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения {file.filename}: {e}")
            logger.finish_error(error=str(e))
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

