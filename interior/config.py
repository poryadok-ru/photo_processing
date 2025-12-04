"""
Конфигурация для обработки интерьеров
Использует новый сервис категорий
"""
from typing import Dict
from core.config import config
from api.services.category_service import CategoryService

# Сервис категорий
_category_service = CategoryService()


class Config:
    """Конфигурация для обработки интерьеров"""
    
    API_KEY = config.openai.api_key
    MODEL_NAME = config.openai.model_name
    IMAGE_MODEL = config.openai.image_model
    BASE_URL = config.openai.base_url
    #PORADOCK_LOG_TOKEN_INTERIOR = config.app.log_token
    
    BASE_DIR = config.app.interior_dir
    INPUT_DIR = config.app.interior_dir / "input"
    OUTPUT_DIR = config.app.interior_dir / "output"
    TEMP_DIR = config.app.interior_dir / "temp"
    
    @classmethod
    def get_thematic_categories(cls) -> Dict[str, Dict[str, str]]:
        """Тематические категории - загружаются из БД через сервис"""
        return _category_service.get_all_categories()
    
    @classmethod
    def reload_categories(cls):
        """Перезагружает категории из БД"""
        _category_service.reload_cache()


class ThematicCategoriesDescriptor:
    """Дескриптор для доступа к категориям через атрибут"""
    def __get__(self, obj, objtype=None):
        return Config.get_thematic_categories()


Config.THEMATIC_SUBCATEGORIES = ThematicCategoriesDescriptor()
