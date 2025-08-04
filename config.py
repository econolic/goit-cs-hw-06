#!/usr/bin/env python3
"""
Конфігурація для вебзастосунку
"""

import os
from pathlib import Path

class Config:
    """Базовий клас конфігурації"""
    
    # Серверні налаштування
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "3000"))
    SOCKET_HOST: str = os.getenv("SOCKET_HOST", "0.0.0.0")
    SOCKET_PORT: int = int(os.getenv("SOCKET_PORT", "5000"))
    
    # MongoDB налаштування
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
    DB_NAME: str = os.getenv("DB_NAME", "messages_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "messages")
    
    # MongoDB Connection Pool налаштування
    MONGO_MAX_POOL_SIZE: int = int(os.getenv("MONGO_MAX_POOL_SIZE", "50"))
    MONGO_MIN_POOL_SIZE: int = int(os.getenv("MONGO_MIN_POOL_SIZE", "5"))
    MONGO_MAX_IDLE_TIME_MS: int = int(os.getenv("MONGO_MAX_IDLE_TIME_MS", "30000"))
    MONGO_WAIT_QUEUE_TIMEOUT_MS: int = int(os.getenv("MONGO_WAIT_QUEUE_TIMEOUT_MS", "5000"))
    
    # ThreadPoolExecutor налаштування
    THREAD_POOL_MAX_WORKERS: int = int(os.getenv("THREAD_POOL_MAX_WORKERS", "10"))
    THREAD_NAME_PREFIX: str = os.getenv("THREAD_NAME_PREFIX", "SocketWorker")
    
    # Socket налаштування
    SOCKET_TIMEOUT: float = float(os.getenv("SOCKET_TIMEOUT", "30.0"))
    SOCKET_BACKLOG: int = int(os.getenv("SOCKET_BACKLOG", "10"))
    SOCKET_BUFFER_SIZE: int = int(os.getenv("SOCKET_BUFFER_SIZE", "1024"))
    
    # Logging налаштування
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Файлові шляхи
    BASE_DIR: Path = Path(__file__).parent
    FRONT_DIR: Path = BASE_DIR / "front-init"
    
    @classmethod
    def validate(cls) -> bool:
        """Валідація конфігурації"""
        try:
            # Перевірка портів
            if not (1 <= cls.HTTP_PORT <= 65535):
                raise ValueError(f"Invalid HTTP_PORT: {cls.HTTP_PORT}")
            if not (1 <= cls.SOCKET_PORT <= 65535):
                raise ValueError(f"Invalid SOCKET_PORT: {cls.SOCKET_PORT}")
            
            # Перевірка директорій
            if not cls.FRONT_DIR.exists():
                raise ValueError(f"FRONT_DIR does not exist: {cls.FRONT_DIR}")
            
            # Перевірка MongoDB налаштувань
            if cls.MONGO_MAX_POOL_SIZE < cls.MONGO_MIN_POOL_SIZE:
                raise ValueError("MONGO_MAX_POOL_SIZE must be >= MONGO_MIN_POOL_SIZE")
            
            return True
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False

class DevelopmentConfig(Config):
    """Конфігурація для розробки"""
    LOG_LEVEL = "DEBUG"
    # MONGO_URI наслідується від базового класу (mongodb://mongodb:27017/)

class ProductionConfig(Config):
    """Конфігурація для продакшену"""
    LOG_LEVEL = "WARNING"
    THREAD_POOL_MAX_WORKERS = 20
    MONGO_MAX_POOL_SIZE = 100

class TestingConfig(Config):
    """Конфігурація для тестування"""
    DB_NAME = "test_messages_db"
    LOG_LEVEL = "DEBUG"
    MONGO_MAX_POOL_SIZE = 10

# Автоматичний вибір конфігурації на основі змінної середовища
def get_config() -> Config:
    """Отримання конфігурації на основі змінної ENVIRONMENT"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()

# Експорт поточної конфігурації
config = get_config()
