"""
Репозиторий для работы с тематическими категориями
"""
from typing import Dict, List
from database.models import ThematicCategory
from database.db_session import get_db


class CategoryRepository:
    """Репозиторий для работы с категориями"""
    
    @staticmethod
    def get_all() -> Dict[str, Dict[str, str]]:
        """Получить все категории в формате {main_category: {subcategory: description}}"""
        with get_db() as db:
            categories = db.query(ThematicCategory).all()
            
            result = {}
            for cat in categories:
                if cat.main_category not in result:
                    result[cat.main_category] = {}
                result[cat.main_category][cat.subcategory] = cat.description
            
            return result
    
    @staticmethod
    def get_by_main_category(main_category: str) -> Dict[str, str]:
        """Получить подкатегории для основной категории"""
        with get_db() as db:
            categories = db.query(ThematicCategory).filter(
                ThematicCategory.main_category == main_category
            ).all()
            
            return {cat.subcategory: cat.description for cat in categories}
    
    @staticmethod
    def create(main_category: str, subcategory: str, description: str) -> ThematicCategory:
        """Создать новую категорию"""
        with get_db() as db:
            category = ThematicCategory(
                main_category=main_category,
                subcategory=subcategory,
                description=description
            )
            db.add(category)
            db.commit()
            db.refresh(category)
            return category

