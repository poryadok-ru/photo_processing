from datetime import datetime, timezone
from log import Log
from core.config import config

class CustomLogger:
    """Кастомный логгер для API с поддержкой двух типов обработки"""
    
    def __init__(self, processing_type: str):
        self.processing_type = processing_type
        self.period_from = datetime.now(timezone.utc)
        
        if processing_type == "white":
            token = config.pixian.log_token
        else: 
            token = config.openai.log_token
            
        if not token:
            raise ValueError(f"Token for {processing_type} processing not found")
            
        self.logger = Log(token=token, auto_host=True)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def critical(self, msg: str):
        self.logger.critical(msg)
    
    def finish_success(self, **kwargs):
        period_to = datetime.now(timezone.utc)
        self.logger.finish_success(self.period_from, period_to, **kwargs)
    
    def finish_warning(self, **kwargs):
        period_to = datetime.now(timezone.utc)
        self.logger.finish_warning(self.period_from, period_to, **kwargs)
    
    def finish_error(self, **kwargs):
        period_to = datetime.now(timezone.utc)
        self.logger.finish_error(self.period_from, period_to, **kwargs)
    
    def finish_log(self, status, **kwargs):
        period_to = datetime.now(timezone.utc)
        self.logger.finish_log(self.period_from, period_to, status=status, **kwargs)