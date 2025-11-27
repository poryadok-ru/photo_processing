"""
Handlers для API endpoints
"""
from .auth_handler import AuthHandler
from .task_handler import TaskHandler
from .processing_handler import ProcessingHandler

__all__ = [
    "AuthHandler",
    "TaskHandler",
    "ProcessingHandler"
]

