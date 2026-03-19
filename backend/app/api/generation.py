"""
歌词生成 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models.models import TrainedModel, Generation
from app.schemas.schemas import (
    GenerationRequest, GenerationResponse,
    MessageResponse
)
from app.services import generation_service, GenerationConfig

router = APIRouter()


@router.post("/generate", response_model=GenerationResponse)
async def generate_lyrics(
    data: GenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    生成歌词
    
    支持三种模式：
    - continue: 续写模式，基于输入文本继续生成
    - topic: 主题模式，基于主题词生成
    - random: 随机模式，随机生成
    """
    # 检查模型是否存在
    model = await db.execute(
        select(TrainedModel).where(TrainedModel.id == data.model_id)
    )
    model_obj = model.scalar_one_or_none()
    
    if not model_obj:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 检查模型状态（允许使用模板生成即使未训练）
    # if model_obj.status != "completed":
    #     raise HTTPException(status_code=400, detail="模型尚未训练完成")
    
    # 创建生成配置
    config = None
    if data.config:
        config = GenerationConfig(
            temperature=data.config.temperature,
            top_p=data.config.top_p,
            top_k=data.config.top_k,
            max_length=data.config.max_length,
            repetition_penalty=data.config.repetition_penalty
        )
    else:
        config = GenerationConfig()
    
    # 调用生成服务
    try:
        result = await generation_service.generate(
            model_id=data.model_id,
            mode=data.mode,
            prompt=data.input_text,
            topic=data.input_text if data.mode == "topic" else None,
            config=config
        )
        
        # 保存生成记录
        generation = Generation(
            model_id=data.model_id,
            input_text=data.input_text,
            output_text=result.text,
            parameters=config.__dict__ if config else None
        )
        db.add(generation)
        await db.flush()
        await db.refresh(generation)
        
        return GenerationResponse(
            **generation.__dict__
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/batch", response_model=List[GenerationResponse])
async def batch_generate(
    data: GenerationRequest,
    count: int = Query(3, ge=1, le=10, description="生成数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    批量生成歌词
    
    一次生成多个版本的歌词供选择
    """
    # 检查模型是否存在
    model = await db.execute(
        select(TrainedModel).where(TrainedModel.id == data.model_id)
    )
    model_obj = model.scalar_one_or_none()
    
    if not model_obj:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 创建生成配置
    config = GenerationConfig()
    if data.config:
        config = GenerationConfig(
            temperature=data.config.temperature,
            top_p=data.config.top_p,
            top_k=data.config.top_k,
            max_length=data.config.max_length,
            repetition_penalty=data.config.repetition_penalty
        )
    
    results = []
    for i in range(count):
        try:
            # 每次生成稍微调整温度增加多样性
            varied_config = GenerationConfig(
                temperature=config.temperature + i * 0.05,
                top_p=config.top_p,
                top_k=config.top_k,
                max_length=config.max_length,
                repetition_penalty=config.repetition_penalty
            )
            
            result = await generation_service.generate(
                model_id=data.model_id,
                mode=data.mode,
                prompt=data.input_text,
                topic=data.input_text if data.mode == "topic" else None,
                config=varied_config
            )
            
            # 保存生成记录
            generation = Generation(
                model_id=data.model_id,
                input_text=data.input_text,
                output_text=result.text,
                parameters=varied_config.__dict__
            )
            db.add(generation)
            await db.flush()
            await db.refresh(generation)
            
            results.append(GenerationResponse(**generation.__dict__))
            
        except Exception as e:
            # 单个失败不影响整体
            continue
    
    if not results:
        raise HTTPException(status_code=500, detail="批量生成失败")
    
    return results


@router.get("/history", response_model=List[GenerationResponse])
async def get_generation_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    model_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取生成历史"""
    query = select(Generation)
    
    if model_id:
        query = query.where(Generation.model_id == model_id)
    
    query = query.offset(skip).limit(limit).order_by(Generation.created_at.desc())
    result = await db.execute(query)
    generations = result.scalars().all()
    
    return [GenerationResponse(**g.__dict__) for g in generations]


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取生成详情"""
    result = await db.execute(
        select(Generation).where(Generation.id == generation_id)
    )
    generation = result.scalar_one_or_none()
    
    if not generation:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    
    return GenerationResponse(**generation.__dict__)


@router.post("/{generation_id}/save", response_model=MessageResponse)
async def save_generation(
    generation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """保存生成结果"""
    result = await db.execute(
        select(Generation).where(Generation.id == generation_id)
    )
    generation = result.scalar_one_or_none()
    
    if not generation:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    
    generation.is_saved = True
    await db.flush()
    
    return MessageResponse(message="保存成功")


@router.post("/{generation_id}/rate", response_model=MessageResponse)
async def rate_generation(
    generation_id: int,
    rating: int = Query(..., ge=1, le=5),
    db: AsyncSession = Depends(get_db)
):
    """为生成结果评分"""
    result = await db.execute(
        select(Generation).where(Generation.id == generation_id)
    )
    generation = result.scalar_one_or_none()
    
    if not generation:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    
    generation.rating = rating
    await db.flush()
    
    return MessageResponse(message="评分成功")


@router.delete("/{generation_id}", response_model=MessageResponse)
async def delete_generation(
    generation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除生成记录"""
    result = await db.execute(
        select(Generation).where(Generation.id == generation_id)
    )
    generation = result.scalar_one_or_none()
    
    if not generation:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    
    await db.delete(generation)
    
    return MessageResponse(message="删除成功")


@router.get("/saved", response_model=List[GenerationResponse])
async def get_saved_generations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取已保存的生成结果"""
    result = await db.execute(
        select(Generation)
        .where(Generation.is_saved == True)
        .offset(skip)
        .limit(limit)
        .order_by(Generation.created_at.desc())
    )
    generations = result.scalars().all()
    
    return [GenerationResponse(**g.__dict__) for g in generations]
