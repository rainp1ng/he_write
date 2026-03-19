"""
作词人 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.models.models import Lyricist, LyricsSample, TrainedModel
from app.schemas.schemas import (
    LyricistCreate, LyricistUpdate, LyricistResponse,
    CrawlRequest, CrawlStatusResponse,
    MessageResponse
)
from app.services import crawler_service, LyricsCleaner

router = APIRouter()

# 存储爬取任务状态
crawl_tasks: dict = {}


@router.get("/", response_model=List[LyricistResponse])
async def list_lyricists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db)
):
    """获取作词人列表"""
    query = select(Lyricist)
    
    if search:
        query = query.where(
            Lyricist.name.contains(search) | 
            Lyricist.alias.contains(search)
        )
    
    query = query.offset(skip).limit(limit).order_by(Lyricist.created_at.desc())
    result = await db.execute(query)
    lyricists = result.scalars().all()
    
    # 获取关联数据计数
    response = []
    for lyricist in lyricists:
        # 获取样本数量
        sample_count_query = select(func.count()).select_from(LyricsSample).where(
            LyricsSample.lyricist_id == lyricist.id
        )
        sample_count = (await db.execute(sample_count_query)).scalar()
        
        # 获取模型数量
        model_count_query = select(func.count()).select_from(TrainedModel).where(
            TrainedModel.lyricist_id == lyricist.id
        )
        model_count = (await db.execute(model_count_query)).scalar()
        
        lyricist_dict = {
            **lyricist.__dict__,
            "sample_count": sample_count or 0,
            "model_count": model_count or 0
        }
        response.append(LyricistResponse.model_validate(lyricist_dict))
    
    return response


@router.post("/", response_model=LyricistResponse)
async def create_lyricist(
    data: LyricistCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建作词人"""
    # 检查是否已存在
    existing = await db.execute(
        select(Lyricist).where(Lyricist.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该作词人已存在")
    
    lyricist = Lyricist(**data.model_dump())
    db.add(lyricist)
    await db.flush()
    await db.refresh(lyricist)
    
    return LyricistResponse(
        **lyricist.__dict__,
        sample_count=0,
        model_count=0
    )


@router.get("/{lyricist_id}", response_model=LyricistResponse)
async def get_lyricist(
    lyricist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取作词人详情"""
    result = await db.execute(
        select(Lyricist).where(Lyricist.id == lyricist_id)
    )
    lyricist = result.scalar_one_or_none()
    
    if not lyricist:
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    # 获取样本数量
    sample_count = (await db.execute(
        select(func.count()).select_from(LyricsSample).where(
            LyricsSample.lyricist_id == lyricist.id
        )
    )).scalar()
    
    # 获取模型数量
    model_count = (await db.execute(
        select(func.count()).select_from(TrainedModel).where(
            TrainedModel.lyricist_id == lyricist.id
        )
    )).scalar()
    
    return LyricistResponse(
        **lyricist.__dict__,
        sample_count=sample_count or 0,
        model_count=model_count or 0
    )


@router.put("/{lyricist_id}", response_model=LyricistResponse)
async def update_lyricist(
    lyricist_id: int,
    data: LyricistUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新作词人"""
    result = await db.execute(
        select(Lyricist).where(Lyricist.id == lyricist_id)
    )
    lyricist = result.scalar_one_or_none()
    
    if not lyricist:
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lyricist, key, value)
    
    await db.flush()
    await db.refresh(lyricist)
    
    # 获取计数
    sample_count = (await db.execute(
        select(func.count()).select_from(LyricsSample).where(
            LyricsSample.lyricist_id == lyricist.id
        )
    )).scalar()
    
    model_count = (await db.execute(
        select(func.count()).select_from(TrainedModel).where(
            TrainedModel.lyricist_id == lyricist.id
        )
    )).scalar()
    
    return LyricistResponse(
        **lyricist.__dict__,
        sample_count=sample_count or 0,
        model_count=model_count or 0
    )


@router.delete("/{lyricist_id}", response_model=MessageResponse)
async def delete_lyricist(
    lyricist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除作词人"""
    result = await db.execute(
        select(Lyricist).where(Lyricist.id == lyricist_id)
    )
    lyricist = result.scalar_one_or_none()
    
    if not lyricist:
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    await db.delete(lyricist)
    
    return MessageResponse(message="删除成功")


@router.post("/{lyricist_id}/crawl", response_model=CrawlStatusResponse)
async def start_crawl(
    lyricist_id: int,
    request: CrawlRequest = CrawlRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    开始采集歌词
    
    从指定的数据源采集作词人的歌词
    """
    # 检查作词人是否存在
    result = await db.execute(
        select(Lyricist).where(Lyricist.id == lyricist_id)
    )
    lyricist = result.scalar_one_or_none()
    
    if not lyricist:
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    # 检查是否已有任务在运行
    if lyricist_id in crawl_tasks and crawl_tasks[lyricist_id].get("status") == "running":
        raise HTTPException(status_code=400, detail="已有采集任务在运行")
    
    # 初始化任务状态
    crawl_tasks[lyricist_id] = {
        "status": "running",
        "found": 0,
        "saved": 0,
        "errors": []
    }
    
    # 在后台执行爬取任务
    async def run_crawl():
        try:
            results, progress = await crawler_service.crawl_lyricist(
                lyricist_id=lyricist_id,
                lyricist_name=lyricist.name,
                sources=request.sources,
                max_samples=request.max_samples
            )
            
            # 保存爬取结果
            saved = 0
            for item in results:
                # 检查是否已存在相同内容
                existing = await db.execute(
                    select(LyricsSample).where(
                        LyricsSample.lyricist_id == lyricist_id,
                        LyricsSample.title == item.title
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                sample = LyricsSample(
                    lyricist_id=lyricist_id,
                    title=item.title,
                    content=item.content,
                    source=item.source,
                    source_url=item.source_url,
                    year=item.year,
                    quality_score=item.quality_score,
                    status="pending"  # 待审核
                )
                db.add(sample)
                saved += 1
            
            await db.flush()
            
            crawl_tasks[lyricist_id] = {
                "status": "completed",
                "found": len(results),
                "saved": saved,
                "errors": progress.errors
            }
            
        except Exception as e:
            crawl_tasks[lyricist_id] = {
                "status": "failed",
                "found": 0,
                "saved": 0,
                "errors": [str(e)]
            }
    
    background_tasks.add_task(run_crawl)
    
    return CrawlStatusResponse(
        lyricist_id=lyricist_id,
        status="running",
        found=0,
        saved=0,
        errors=[]
    )


@router.get("/{lyricist_id}/crawl/status", response_model=CrawlStatusResponse)
async def get_crawl_status(lyricist_id: int):
    """获取采集任务状态"""
    if lyricist_id not in crawl_tasks:
        return CrawlStatusResponse(
            lyricist_id=lyricist_id,
            status="idle",
            found=0,
            saved=0,
            errors=[]
        )
    
    task = crawl_tasks[lyricist_id]
    return CrawlStatusResponse(
        lyricist_id=lyricist_id,
        status=task.get("status", "idle"),
        found=task.get("found", 0),
        saved=task.get("saved", 0),
        errors=task.get("errors", [])
    )


@router.post("/{lyricist_id}/crawl/stop", response_model=MessageResponse)
async def stop_crawl(lyricist_id: int):
    """停止采集任务"""
    crawler_service.stop_crawl(lyricist_id)
    
    if lyricist_id in crawl_tasks:
        crawl_tasks[lyricist_id]["status"] = "stopped"
    
    return MessageResponse(message="已发送停止信号")
