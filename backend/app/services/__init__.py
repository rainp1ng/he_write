"""
he_write 服务层

提供歌词爬取、模型训练、歌词生成等核心功能。
"""
from app.services.crawler_service import (
    crawler_service,
    CrawlerService,
    LyricCrawler,
    CrawlResult,
    CrawlProgress,
    LyricsCleaner
)

from app.services.training_service import (
    training_service,
    TrainingService,
    TrainingConfig,
    TrainingProgress,
    TextPreprocessor,
    NGramModel,
    MarkovModel
)

from app.services.generation_service import (
    generation_service,
    GenerationService,
    GenerationConfig,
    GenerationResult,
    LyricsGenerator,
    LyricsPostProcessor
)

__all__ = [
    # Crawler
    'crawler_service',
    'CrawlerService',
    'LyricCrawler',
    'CrawlResult',
    'CrawlProgress',
    'LyricsCleaner',
    
    # Training
    'training_service',
    'TrainingService',
    'TrainingConfig',
    'TrainingProgress',
    'TextPreprocessor',
    'NGramModel',
    'MarkovModel',
    
    # Generation
    'generation_service',
    'GenerationService',
    'GenerationConfig',
    'GenerationResult',
    'LyricsGenerator',
    'LyricsPostProcessor',
]
