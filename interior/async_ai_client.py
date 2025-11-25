import base64
import io
from openai import AsyncOpenAI
from PIL import Image
import asyncio
from typing import Tuple, Optional
from interior.config import Config
from api.logging import CustomLogger

class AsyncAIClient:
    """Асинхронный клиент для работы с AI API"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=Config.API_KEY,
            base_url=Config.BASE_URL
        )
    
    async def analyze_thematic_subcategory(self, image_data: bytes, logger: CustomLogger) -> Tuple[str, str]:
        """Асинхронно анализирует тематику товара"""
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        system_prompt = """Ты эксперт по категоризации товаров маркетплейса..."""  # ваш промпт
        
        try:
            response = await self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Определи категорию и подкатегорию этого товара:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            result = response.choices[0].message.content.strip()
            if "|" in result:
                return result.split("|")
            else:
                return "LIVING_ROOM", "DECOR"
                
        except Exception as e:
            logger.error(f"Ошибка анализа категории: {e}")
            return "LIVING_ROOM", "DECOR"
    
    async def edit_image_with_gemini(self, image_data: bytes, prompt: str, logger: CustomLogger) -> Optional[bytes]:
        """Асинхронно генерирует изображение"""
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        try:
            response = await self.client.chat.completions.create(
                model=Config.IMAGE_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                max_tokens=1000
            )
            
            msg = response.choices[0].message
            if hasattr(msg, "image") and msg.image and "url" in msg.image:
                img_url = msg.image["url"]
                if "base64," in img_url:
                    base64_data = img_url.split("base64,")[1]
                    return base64.b64decode(base64_data)
            
            logger.error("В ответе не найдено изображение")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None