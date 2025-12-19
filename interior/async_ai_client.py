import base64
import io
from openai import AsyncOpenAI
from PIL import Image
import asyncio
from interior.config import Config
from api.logging import CustomLogger
from core.config import config
import re
import csv
import httpx
from io import StringIO
from typing import Optional, Tuple, Dict
import time


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
            #print(f"API response message: {msg}")
            #print(f"Message type: {type(msg)}")
            #print(f"Message attributes: {dir(msg)}")
            
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
            
            #print(f"В ответе не найдено изображение. img_url: {img_url}")
            #print(f"msg.images: {getattr(msg, 'images', 'N/A')}")
            #print(f"msg.image: {getattr(msg, 'image', 'N/A')}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            import traceback
            traceback.print_exc()
            return None
            import re

SHEET_ID = config.app.sheet_id
GID = config.app.gid

def extract_six_digit_code(filename: str) -> Optional[str]:
    m = re.search(r'(?<!\d)(\d{6})(?!\d)', filename)
    return m.group(1) if m else None

async def get_product_from_sheet_by_code(code: str, logger) -> Optional[Tuple[str, str]]:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}&_cb={int(time.time())}"
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "User-Agent": "httpx/SheetsFetcher",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                body_sample = resp.text[:800] if resp.text else ""
                logger.error(
                    "Не удалось загрузить Google Sheet: HTTPStatusError | "
                    f"status={resp.status_code} url={resp.request.url} "
                    f"headers={dict(resp.headers)} "
                    f"body_sample={body_sample!r} exc={e!r}"
                )
                return None
    except httpx.TimeoutException as e:
        logger.error(
            "Не удалось загрузить Google Sheet: Timeout | "
            f"url={url} exc={e!r}\n{traceback.format_exc()}"
        )
        return None
    except httpx.RequestError as e:
        # ConnectError, NetworkError и пр. наследуются от RequestError
        req_url = getattr(e.request, "url", url)
        logger.error(
            "Не удалось загрузить Google Sheet: RequestError | "
            f"url={req_url} exc={e!r}\n{traceback.format_exc()}"
        )
        return None
    except Exception as e:
        logger.error(
            "Не удалось загрузить Google Sheet: Unexpected error | "
            f"url={url} exc={e!r}\n{traceback.format_exc()}"
        )
        return None

    # Если сюда дошли — статус 200
    try:
        text = resp.content.decode("utf-8-sig", errors="replace")
    except Exception as e:
        logger.error(
            f"Ошибка декодирования CSV: exc={e!r} "
            f"raw_sample={resp.content[:200]!r}\n{traceback.format_exc()}"
        )
        return None

    try:
        reader = csv.DictReader(StringIO(text))
        for row in reader:
            kod = (row.get("Код") or "").strip()
            m = re.search(r'(?<!\d)(\d{6})(?!\d)', kod)
            if not m:
                continue
            if m.group(1) == code:
                segment = (row.get("Сегмент") or "").strip()
                product_name = (row.get("Номенклатура") or "").strip()
                return segment, product_name

        # Код не найден — логируем список всех кодов для диагностики
        # Соберём первые N кодов, чтобы не захламлять логи
        reader = csv.DictReader(StringIO(text))  # перечитываем
        all_codes = []
        for row in reader:
            kod = (row.get("Код") or "").strip()
            m = re.search(r'(?<!\d)(\d{6})(?!\d)', kod)
            if m:
                all_codes.append(m.group(1))
        sample_codes = ", ".join(all_codes[:100])
        logger.error(
            f"Код {code} не найден в Google Sheets. Всего кодов: {len(all_codes)}. "
            f"Первые коды: {sample_codes}"
        )
        return None

    except Exception as e:
        logger.error(
            f"Ошибка разбора CSV: exc={e!r}\n{traceback.format_exc()}"
        )
        return None