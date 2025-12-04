from pathlib import Path
from core.config import config

class Config:
    """Конфигурация для обработки белого фона"""
    
    PIXIAN_API_URL = config.pixian.api_url
    PIXIAN_API_USER = config.pixian.api_user
    PIXIAN_API_KEY = config.pixian.api_key
    #PORADOCK_LOG_TOKEN_WHITE = config.app.log_token
    
    # Пути
    BASE_DIR = Path(__file__).parent
    INPUT_DIR = BASE_DIR / "input"
    OUTPUT_DIR = BASE_DIR / "output"
    
    # Поддерживаемые форматы изображений
    SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".webp"]
    
    BACKGROUND_COLOR = config.pixian.background_color
    TEST_MODE = config.pixian.test_mode
    TIMEOUT = config.pixian.timeout
    TARGET_SIZE = config.pixian.target_size
    
    @classmethod
    def validate_config(cls):
        """Проверяет корректность конфигурации"""
        if not cls.PIXIAN_API_USER or not cls.PIXIAN_API_KEY:
            raise ValueError("Переменные окружения PIXIAN_API_USER и PIXIAN_API_KEY не заданы.")
        
        if not cls.INPUT_DIR.exists():
            raise FileNotFoundError(f"Папка {cls.INPUT_DIR} не найдена.")
        
        # Создаем папку вывода
        cls.OUTPUT_DIR.mkdir(exist_ok=True)