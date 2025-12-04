from datetime import datetime, timezone
from log import Log
from core.config import config

class CustomLogger:
    """Кастомный логгер для API с поддержкой двух типов обработки"""
    
    def __init__(self, processing_type: str):
        self.processing_type = processing_type
        self.period_from = datetime.now(timezone.utc)
        
        token = config.app.log_token
        
        if not token:
            import logging
            self.logger = logging.getLogger(f"photo_processing.{processing_type}")
            self._use_std_logging = True
        else:
            self.logger = Log(token=token, auto_host=True)
            self._use_std_logging = False
    
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
        if self._use_std_logging:
            self.logger.info(f"SUCCESS: {kwargs}")
        else:
            self.logger.finish_success(self.period_from, period_to, **kwargs)
    
    def finish_warning(self, **kwargs):
        period_to = datetime.now(timezone.utc)
        if self._use_std_logging:
            self.logger.warning(f"WARNING: {kwargs}")
        else:
            self.logger.finish_warning(self.period_from, period_to, **kwargs)
    
    def finish_error(self, **kwargs):
        period_to = datetime.now(timezone.utc)
        if self._use_std_logging:
            self.logger.error(f"ERROR: {kwargs}")
        else:
            self.logger.finish_error(self.period_from, period_to, **kwargs)
    
    def finish_log(self, status, **kwargs):
        period_to = datetime.now(timezone.utc)
        if self._use_std_logging:
            self.logger.info(f"FINISH [{status}]: {kwargs}")
        else:
            self.logger.finish_log(self.period_from, period_to, status=status, **kwargs)