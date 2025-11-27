from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator
import logging
from core.config import config

logger = logging.getLogger(__name__)

engine = create_engine(
    config.database.url,
    echo=config.sql_debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  
    pool_recycle=3600,   
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с БД.
    
    Пример:
        with get_db() as db:
            user = db.query(User).filter(User.username == "admin").first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        db.close()


def init_db():
    """Создание таблиц"""
    from .models import Base
    Base.metadata.create_all(bind=engine)

