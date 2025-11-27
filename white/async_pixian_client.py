import aiohttp
import asyncio
from typing import Optional, Tuple
from white.config import Config
from api.logging import CustomLogger

class AsyncPixianClient:
    """Асинхронный клиент для Pixian.AI API"""
    
    def __init__(self):
        self.api_url = Config.PIXIAN_API_URL or "https://api.pixian.ai/api/v2/remove-background"
        self.auth = aiohttp.BasicAuth(
            login=Config.PIXIAN_API_USER,
            password=Config.PIXIAN_API_KEY
        )
        self.timeout = aiohttp.ClientTimeout(total=Config.TIMEOUT)
    
    async def remove_background(self, image_data: bytes, logger: CustomLogger) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Асинхронно удаляет фон изображения
        
        Args:
            image_data: Данные изображения в bytes
            logger: Логгер для записи сообщений
            
        Returns:
            tuple: (success, image_data, error_message)
        """
        try:
            form_data = aiohttp.FormData()
            form_data.add_field('image', image_data, filename='image.jpg', content_type='image/jpeg')
            form_data.add_field('background.color', Config.BACKGROUND_COLOR)
            form_data.add_field('result.target_size', Config.TARGET_SIZE)
            form_data.add_field('test', Config.TEST_MODE)
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.api_url,
                    data=form_data,
                    auth=self.auth
                ) as response:
                    
                    if response.status == 200:
                        processed_data = await response.read()
                        return True, processed_data, None
                    else:
                        error_text = await response.text()
                        return False, None, f"HTTP {response.status}: {error_text}"
                        
        except asyncio.TimeoutError:
            return False, None, "Request timeout"
        except aiohttp.ClientError as e:
            return False, None, f"Client error: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"