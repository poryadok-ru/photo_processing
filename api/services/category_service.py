"""
Сервис для работы с категориями
"""
from typing import Dict
from api.repositories import CategoryRepository


class CategoryService:
    """Сервис для работы с категориями"""
    
    def __init__(self, category_repo: CategoryRepository = None):
        self.category_repo = category_repo or CategoryRepository()
        self._cache: Dict[str, Dict[str, str]] = None
    
    def get_all_categories(self, use_cache: bool = True) -> Dict[str, Dict[str, str]]:
        """Получить все категории (с кэшированием)"""
        if use_cache and self._cache is not None:
            return self._cache
        
        self._cache = self.category_repo.get_all()
        return self._cache
    
    def reload_cache(self):
        """Перезагрузить кэш"""
        self._cache = None
        self.get_all_categories()

