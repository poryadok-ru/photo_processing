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
        
        system_prompt = """Ты эксперт по категоризации товаров маркетплейса.
        Твоя задача — определить категорию и подкатегорию товара по фото.
        Ответ строго в формате: КАТЕГОРИЯ|ПОДКАТЕГОРИЯ
        
        Особое правило:
        - Если изображены праздничные украшения (ёлочные игрушки, новогодние, пасхальные, хэллоуинские предметы и т.п.), 
          отнеси их к категории HOLIDAY с соответствующей подкатегорией:
          CHRISTMAS, EASTER, HALLOWEEN, NEW_YEAR, VALENTINE или GENERAL.
        
        Остальные доступные категории и подкатегории:
        KITCHEN - COOKWARE, UTENSILS, APPLIANCES, STORAGE, DINNERWARE, DECOR
        BATHROOM - TOWELS, HYGIENE, FURNITURE, STORAGE, ACCESSORIES, CLEANING  
        LIVING_ROOM - FURNITURE, LIGHTING, DECOR, TEXTILES, STORAGE, ELECTRONICS
        BEDROOM - BEDDING, FURNITURE, LIGHTING, DECOR, STORAGE, TEXTILES
        GARDEN - FURNITURE, TOOLS, DECOR, PLANTS, LIGHTING, STORAGE
        OFFICE - FURNITURE, ORGANIZATION, STATIONERY, TECH, DECOR
        HOLIDAY - CHRISTMAS, EASTER, HALLOWEEN, NEW_YEAR, VALENTINE, GENERAL"""
        
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
        """Асинхронно генерирует изображение (совместимость с Gemini 2.5)"""
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
            
            # Пробуем извлечь изображение из разных возможных полей
            img_url = None
            
            # Новый формат Gemini 2.5
            if hasattr(msg, "images") and msg.images:
                img_obj = msg.images[0] if isinstance(msg.images, list) and len(msg.images) > 0 else None
                if img_obj:
                    if isinstance(img_obj, dict):
                        img_url = img_obj.get('image_url', {}).get('url', img_obj.get('url'))
                    elif hasattr(img_obj, 'url'):
                        img_url = img_obj.url
                    elif isinstance(img_obj, str):
                        img_url = img_obj
            
            # Старый формат (для обратной совместимости)
            if not img_url and hasattr(msg, "image") and msg.image:
                if isinstance(msg.image, dict):
                    img_url = msg.image.get("url")
                elif hasattr(msg.image, "url"):
                    img_url = msg.image.url
            
            # Декодируем если нашли URL
            if img_url and "base64," in img_url:
                base64_data = img_url.split("base64,")[1]
                return base64.b64decode(base64_data)
            
            print("В ответе не найдено изображение")
            return None
            
        except Exception as e:
            print(f"Ошибка генерации изображения: {e}")
            import traceback
            traceback.print_exc()
            return None