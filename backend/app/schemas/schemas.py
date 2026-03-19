"""
Pydantic Schemas for API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 作词人 Schemas ====================

class LyricistBase(BaseModel):
    """作词人基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="作词人姓名")
    alias: Optional[str] = Field(None, max_length=200, description="别名")
    style: Optional[str] = Field(None, max_length=50, description="风格标签")
    description: Optional[str] = Field(None, description="描述")


class LyricistCreate(LyricistBase):
    """创建作词人"""
    pass


class LyricistUpdate(BaseModel):
    """更新作词人"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    alias: Optional[str] = Field(None, max_length=200)
    style: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class LyricistResponse(LyricistBase):
    """作词人响应"""
    id: int
    created_at: datetime
    updated_at: datetime
    sample_count: int = 0
    model_count: int = 0

    class Config:
        from_attributes = True


# ==================== 歌词样本 Schemas ====================

class SampleBase(BaseModel):
    """歌词样本基础模型"""
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=10, description="歌词内容")
    source: Optional[str] = Field(None, max_length=100, description="来源")
    source_url: Optional[str] = Field(None, max_length=500, description="来源 URL")
    year: Optional[int] = Field(None, ge=1900, le=2100, description="年份")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class SampleCreate(SampleBase):
    """创建歌词样本"""
    lyricist_id: int


class SampleUpdate(BaseModel):
    """更新歌词样本"""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    source: Optional[str] = Field(None, max_length=100)
    source_url: Optional[str] = Field(None, max_length=500)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected)$")
    quality_score: Optional[float] = Field(None, ge=0, le=100)


class SampleResponse(SampleBase):
    """歌词样本响应"""
    id: int
    lyricist_id: int
    status: str = "pending"
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    lyricist_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== 模型 Schemas ====================

class ModelConfig(BaseModel):
    """模型训练配置"""
    learning_rate: float = Field(2e-5, ge=1e-7, le=1e-3)
    batch_size: int = Field(8, ge=1, le=64)
    epochs: int = Field(3, ge=1, le=50)
    max_length: int = Field(512, ge=128, le=2048)
    warmup_steps: int = Field(100, ge=0, le=1000)


class ModelCreate(BaseModel):
    """创建训练模型"""
    lyricist_id: int
    name: str = Field(..., min_length=1, max_length=100)
    version: Optional[str] = Field("v1.0", max_length=20)
    base_model: str = Field("gpt2-chinese", description="基础模型")
    config: Optional[ModelConfig] = ModelConfig()


class ModelResponse(BaseModel):
    """模型响应"""
    id: int
    lyricist_id: int
    name: str
    version: Optional[str]
    base_model: Optional[str]
    status: str
    config: Optional[dict] = None
    metrics: Optional[dict] = None
    created_at: datetime
    trained_at: Optional[datetime] = None
    lyricist_name: Optional[str] = None

    class Config:
        from_attributes = True


class TrainingStatusResponse(BaseModel):
    """训练状态响应"""
    model_id: int
    status: str
    progress: float
    current_step: int
    total_steps: int
    logs: Optional[str] = None
    error_message: Optional[str] = None


# ==================== 生成 Schemas ====================

class GenerationConfig(BaseModel):
    """生成配置"""
    temperature: float = Field(0.9, ge=0.1, le=2.0, description="创意度")
    top_p: float = Field(0.95, ge=0.1, le=1.0)
    top_k: int = Field(50, ge=1, le=100)
    max_length: int = Field(256, ge=50, le=1000)
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0)


class GenerationRequest(BaseModel):
    """生成请求"""
    model_id: int
    input_text: Optional[str] = Field(None, description="输入提示文本")
    mode: str = Field("continue", pattern="^(continue|topic|random)$", description="生成模式")
    config: Optional[GenerationConfig] = GenerationConfig()


class GenerationResponse(BaseModel):
    """生成响应"""
    id: int
    model_id: int
    input_text: Optional[str]
    output_text: str
    parameters: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 爬虫 Schemas ====================

class CrawlRequest(BaseModel):
    """爬虫请求"""
    sources: List[str] = Field(["netease"], description="数据源列表")
    max_samples: int = Field(100, ge=1, le=1000, description="最大采集数量")


class CrawlStatusResponse(BaseModel):
    """爬虫状态响应"""
    lyricist_id: int
    status: str
    found: int = 0
    saved: int = 0
    errors: List[str] = []


# ==================== 通用 Schemas ====================

class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int
    items: List


class MessageResponse(BaseModel):
    """消息响应"""
    message: str
    success: bool = True
