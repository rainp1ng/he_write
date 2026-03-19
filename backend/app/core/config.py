"""
核心配置模块
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "he_write"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/he_write.db"
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 模型配置
    MODEL_BASE_PATH: str = "./models"
    DATA_PATH: str = "./data"
    
    # 爬虫配置
    CRAWLER_DELAY: float = 1.0  # 请求间隔（秒）
    CRAWLER_TIMEOUT: int = 30
    
    # 训练配置
    TRAINING_DEVICE: str = "cpu"  # cpu 或 cuda
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# 确保必要目录存在
os.makedirs(settings.MODEL_BASE_PATH, exist_ok=True)
os.makedirs(settings.DATA_PATH, exist_ok=True)
