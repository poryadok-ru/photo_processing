import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL") or "")
    
    def __post_init__(self):
        if not self.url:
            raise ValueError("DATABASE_URL environment variable is required")


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    base_dir: Path = field(default_factory=lambda: Path("/app") if os.path.exists("/app") else Path(__file__).parent.parent.parent)
    white_dir: Path = field(init=False)
    interior_dir: Path = field(init=False)
    
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))) 
    max_files_count: int = field(default_factory=lambda: int(os.getenv("MAX_FILES_COUNT", 50)))
    allowed_content_types: Set[str] = field(default_factory=lambda: {
        "image/jpeg", "image/jpg", "image/png", "image/webp"
    })
    
    task_cleanup_interval_hours: int = field(default_factory=lambda: int(os.getenv("TASK_CLEANUP_INTERVAL_HOURS", 1)))
    task_max_age_hours: int = field(default_factory=lambda: int(os.getenv("TASK_MAX_AGE_HOURS", 24)))
    
    def __post_init__(self):
        self.white_dir = self.base_dir / "white"
        self.interior_dir = self.base_dir / "interior"
        
        (self.white_dir / "input").mkdir(parents=True, exist_ok=True)
        (self.white_dir / "output").mkdir(parents=True, exist_ok=True)
        (self.interior_dir / "input").mkdir(parents=True, exist_ok=True)
        (self.interior_dir / "output").mkdir(parents=True, exist_ok=True)
        (self.interior_dir / "temp").mkdir(parents=True, exist_ok=True)


@dataclass
class OpenAIConfig:
    """Конфигурация OpenAI API"""
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY") or "")
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gpt-4-vision-preview"))
    image_model: str = field(default_factory=lambda: os.getenv("IMAGE_MODEL", "gemini-pro-vision"))
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "https://api.openai.com/v1"))
    log_token: str = field(default_factory=lambda: os.getenv("PORADOCK_LOG_TOKEN_INTERIOR") or "")


@dataclass
class PixianConfig:
    """Конфигурация Pixian API"""
    api_url: str = field(default_factory=lambda: os.getenv("PIXIAN_API_URL", "https://api.pixian.ai/api/v2/remove-background"))
    api_user: str = field(default_factory=lambda: os.getenv("PIXIAN_API_USER") or "")
    api_key: str = field(default_factory=lambda: os.getenv("PIXIAN_API_KEY") or "")
    log_token: str = field(default_factory=lambda: os.getenv("PORADOCK_LOG_TOKEN_WHITE") or "")
    background_color: str = field(default_factory=lambda: os.getenv("PIXIAN_BACKGROUND_COLOR", "FFFFFF"))
    test_mode: str = field(default_factory=lambda: os.getenv("PIXIAN_TEST_MODE", "true"))
    timeout: int = field(default_factory=lambda: int(os.getenv("PIXIAN_TIMEOUT", 120)))


@dataclass
class Config:
    """Главная конфигурация приложения"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    app: AppConfig = field(default_factory=AppConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    pixian: PixianConfig = field(default_factory=PixianConfig)
    
    sql_debug: bool = field(default_factory=lambda: os.getenv("SQL_DEBUG", "false").lower() == "true")


config = Config()

