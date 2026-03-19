"""
SQLAlchemy 数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Lyricist(Base):
    """作词人模型"""
    __tablename__ = "lyricists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    alias = Column(String(200))  # 别名
    style = Column(String(50))   # 风格标签
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    samples = relationship("LyricsSample", back_populates="lyricist", cascade="all, delete-orphan")
    models = relationship("TrainedModel", back_populates="lyricist", cascade="all, delete-orphan")


class LyricsSample(Base):
    """歌词样本模型"""
    __tablename__ = "lyrics_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    lyricist_id = Column(Integer, ForeignKey("lyricists.id"), nullable=False, index=True)
    title = Column(String(200))
    content = Column(Text, nullable=False)
    source = Column(String(100))      # 来源
    source_url = Column(String(500))  # 来源 URL
    year = Column(Integer)            # 年份
    tags = Column(String(200))        # 标签 (JSON 数组字符串)
    quality_score = Column(Float)     # 质量评分
    status = Column(String(20), default="pending")  # pending/approved/rejected
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    lyricist = relationship("Lyricist", back_populates="samples")


class TrainedModel(Base):
    """训练模型元数据"""
    __tablename__ = "trained_models"
    
    id = Column(Integer, primary_key=True, index=True)
    lyricist_id = Column(Integer, ForeignKey("lyricists.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    version = Column(String(20))
    base_model = Column(String(100))  # 基础模型名称
    model_path = Column(String(500))  # 模型文件路径
    config = Column(JSON)             # 训练配置
    metrics = Column(JSON)            # 训练指标
    status = Column(String(20), default="pending")  # pending/training/completed/failed
    created_at = Column(DateTime, server_default=func.now())
    trained_at = Column(DateTime)
    
    # 关系
    lyricist = relationship("Lyricist", back_populates="models")
    generations = relationship("Generation", back_populates="model", cascade="all, delete-orphan")
    training_task = relationship("TrainingTask", back_populates="model", uselist=False, cascade="all, delete-orphan")


class TrainingTask(Base):
    """训练任务"""
    __tablename__ = "training_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("trained_models.id"), nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    progress = Column(Float, default=0.0)           # 0-100
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    logs = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # 关系
    model = relationship("TrainedModel", back_populates="training_task")


class Generation(Base):
    """生成记录"""
    __tablename__ = "generations"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("trained_models.id"), index=True)
    input_text = Column(Text)
    parameters = Column(JSON)          # 生成参数
    output_text = Column(Text)
    rating = Column(Integer)           # 用户评分 1-5
    is_saved = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    model = relationship("TrainedModel", back_populates="generations")
