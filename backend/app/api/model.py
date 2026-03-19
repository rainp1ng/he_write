"""
模型训练 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import json

from app.core.database import get_db
from app.models.models import TrainedModel, TrainingTask, Lyricist, LyricsSample
from app.schemas.schemas import (
    ModelCreate, ModelResponse, TrainingStatusResponse,
    MessageResponse
)
from app.services import training_service, TrainingConfig, TrainingProgress

router = APIRouter()


@router.get("/", response_model=List[ModelResponse])
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    lyricist_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取模型列表"""
    query = select(TrainedModel)
    
    if lyricist_id:
        query = query.where(TrainedModel.lyricist_id == lyricist_id)
    
    if status:
        query = query.where(TrainedModel.status == status)
    
    query = query.offset(skip).limit(limit).order_by(TrainedModel.created_at.desc())
    result = await db.execute(query)
    models = result.scalars().all()
    
    response = []
    for model in models:
        lyricist = await db.execute(
            select(Lyricist.name).where(Lyricist.id == model.lyricist_id)
        )
        lyricist_name = lyricist.scalar()
        
        model_dict = {
            **model.__dict__,
            "lyricist_name": lyricist_name
        }
        response.append(ModelResponse.model_validate(model_dict))
    
    return response


@router.post("/", response_model=ModelResponse)
async def create_model(
    data: ModelCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """创建训练任务"""
    # 检查作词人是否存在
    lyricist = await db.execute(
        select(Lyricist).where(Lyricist.id == data.lyricist_id)
    )
    lyricist_obj = lyricist.scalar_one_or_none()
    if not lyricist_obj:
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    # 检查样本数量
    sample_result = await db.execute(
        select(LyricsSample).where(
            LyricsSample.lyricist_id == data.lyricist_id,
            LyricsSample.status == "approved"
        )
    )
    approved_samples = sample_result.scalars().all()
    
    if len(approved_samples) < 10:
        # 尝试使用 pending 样本
        pending_result = await db.execute(
            select(LyricsSample).where(
                LyricsSample.lyricist_id == data.lyricist_id
            )
        )
        all_samples = pending_result.scalars().all()
        
        if len(all_samples) < 10:
            raise HTTPException(
                status_code=400, 
                detail=f"样本数量不足，至少需要 10 条样本（当前 {len(all_samples)} 条）"
            )
        
        # 使用所有样本
        samples = all_samples
    else:
        samples = approved_samples
    
    # 创建模型记录
    config = data.config.model_dump() if data.config else {}
    model = TrainedModel(
        lyricist_id=data.lyricist_id,
        name=data.name,
        version=data.version,
        base_model=data.base_model,
        config=config,
        status="pending"
    )
    db.add(model)
    await db.flush()
    await db.refresh(model)
    
    # 创建训练任务
    task = TrainingTask(
        model_id=model.id,
        status="pending"
    )
    db.add(task)
    await db.flush()
    
    # 启动后台训练任务
    background_tasks.add_task(
        run_training_task,
        model.id,
        [s.content for s in samples],
        config,
        db
    )
    
    return ModelResponse(
        **model.__dict__,
        lyricist_name=lyricist_obj.name
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取模型详情"""
    result = await db.execute(
        select(TrainedModel).where(TrainedModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    lyricist = await db.execute(
        select(Lyricist.name).where(Lyricist.id == model.lyricist_id)
    )
    lyricist_name = lyricist.scalar()
    
    return ModelResponse(
        **model.__dict__,
        lyricist_name=lyricist_name
    )


@router.get("/{model_id}/status", response_model=TrainingStatusResponse)
async def get_training_status(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取训练状态"""
    result = await db.execute(
        select(TrainedModel).where(TrainedModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    task = await db.execute(
        select(TrainingTask).where(TrainingTask.model_id == model_id)
    )
    task_obj = task.scalar_one_or_none()
    
    if not task_obj:
        return TrainingStatusResponse(
            model_id=model_id,
            status=model.status,
            progress=0,
            current_step=0,
            total_steps=0
        )
    
    return TrainingStatusResponse(
        model_id=model_id,
        status=task_obj.status,
        progress=task_obj.progress,
        current_step=task_obj.current_step,
        total_steps=task_obj.total_steps,
        logs=task_obj.logs,
        error_message=task_obj.error_message
    )


@router.post("/{model_id}/stop", response_model=MessageResponse)
async def stop_training(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """停止训练"""
    result = await db.execute(
        select(TrainingTask).where(TrainingTask.model_id == model_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    
    if task.status != "running":
        raise HTTPException(status_code=400, detail="训练任务未在运行")
    
    # 停止训练服务
    training_service.stop_training(model_id)
    
    # 更新数据库状态
    task.status = "stopped"
    await db.flush()
    
    return MessageResponse(message="已发送停止信号")


@router.delete("/{model_id}", response_model=MessageResponse)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除模型"""
    result = await db.execute(
        select(TrainedModel).where(TrainedModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 检查是否正在训练
    if model.status == "training":
        raise HTTPException(status_code=400, detail="模型正在训练中，请先停止训练")
    
    # 删除模型文件
    training_service.delete_model(model_id)
    
    await db.delete(model)
    
    return MessageResponse(message="删除成功")


async def run_training_task(
    model_id: int,
    samples: List[str],
    config: dict,
    db: AsyncSession
):
    """
    后台训练任务
    
    使用训练服务执行实际的模型训练
    """
    from loguru import logger
    
    try:
        # 获取模型和任务记录
        model_result = await db.execute(
            select(TrainedModel).where(TrainedModel.id == model_id)
        )
        model_obj = model_result.scalar_one_or_none()
        
        task_result = await db.execute(
            select(TrainingTask).where(TrainingTask.model_id == model_id)
        )
        task_obj = task_result.scalar_one_or_none()
        
        if not model_obj or not task_obj:
            logger.error(f"模型或任务不存在: {model_id}")
            return
        
        # 更新状态为训练中
        task_obj.status = "running"
        task_obj.started_at = datetime.utcnow()
        model_obj.status = "training"
        await db.commit()
        
        # 创建训练配置
        training_config = TrainingConfig(
            learning_rate=config.get("learning_rate", 0.001),
            batch_size=config.get("batch_size", 8),
            epochs=config.get("epochs", 3),
            max_length=config.get("max_length", 512),
            ngram_size=config.get("ngram_size", 3)
        )
        
        # 定义进度回调
        def progress_callback(progress: TrainingProgress):
            task_obj.current_step = progress.current_step
            task_obj.total_steps = progress.total_steps
            task_obj.progress = progress.progress
            task_obj.logs = "\n".join(progress.logs[-10:])  # 只保留最近10条日志
            # 异步提交会在外层处理
        
        # 执行训练
        success, progress = await training_service.train_model(
            model_id=model_id,
            samples=samples,
            config=training_config,
            progress_callback=progress_callback
        )
        
        # 更新最终状态
        task_obj.status = progress.status
        task_obj.progress = progress.progress
        task_obj.logs = "\n".join(progress.logs[-20:])
        task_obj.error_message = progress.error_message
        
        if success:
            task_obj.completed_at = datetime.utcnow()
            model_obj.status = "completed"
            model_obj.trained_at = datetime.utcnow()
            model_obj.model_path = f"models/model_{model_id}.pkl"
            model_obj.metrics = progress.metrics
        else:
            model_obj.status = "failed"
        
        await db.commit()
        logger.info(f"模型训练完成: {model_id}, 状态: {progress.status}")
        
    except Exception as e:
        logger.error(f"训练任务失败: {e}")
        
        # 更新失败状态
        try:
            task_result = await db.execute(
                select(TrainingTask).where(TrainingTask.model_id == model_id)
            )
            task_obj = task_result.scalar_one_or_none()
            
            model_result = await db.execute(
                select(TrainedModel).where(TrainedModel.id == model_id)
            )
            model_obj = model_result.scalar_one_or_none()
            
            if task_obj:
                task_obj.status = "failed"
                task_obj.error_message = str(e)
            
            if model_obj:
                model_obj.status = "failed"
            
            await db.commit()
        except Exception as db_error:
            logger.error(f"更新失败状态出错: {db_error}")
