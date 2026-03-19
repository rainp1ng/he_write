"""
歌词样本 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import json

from app.core.database import get_db
from app.models.models import LyricsSample, Lyricist
from app.schemas.schemas import (
    SampleCreate, SampleUpdate, SampleResponse,
    MessageResponse
)

router = APIRouter()


@router.get("/", response_model=List[SampleResponse])
async def list_samples(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    lyricist_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取歌词样本列表"""
    query = select(LyricsSample)
    
    if lyricist_id:
        query = query.where(LyricsSample.lyricist_id == lyricist_id)
    
    if status:
        query = query.where(LyricsSample.status == status)
    
    if search:
        query = query.where(
            LyricsSample.title.contains(search) | 
            LyricsSample.content.contains(search)
        )
    
    query = query.offset(skip).limit(limit).order_by(LyricsSample.created_at.desc())
    result = await db.execute(query)
    samples = result.scalars().all()
    
    # 获取作词人名称
    response = []
    for sample in samples:
        lyricist = await db.execute(
            select(Lyricist.name).where(Lyricist.id == sample.lyricist_id)
        )
        lyricist_name = lyricist.scalar()
        
        sample_dict = {
            **sample.__dict__,
            "lyricist_name": lyricist_name,
            "tags": json.loads(sample.tags) if sample.tags else []
        }
        response.append(SampleResponse.model_validate(sample_dict))
    
    return response


@router.post("/", response_model=SampleResponse)
async def create_sample(
    data: SampleCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建歌词样本"""
    # 检查作词人是否存在
    lyricist = await db.execute(
        select(Lyricist).where(Lyricist.id == data.lyricist_id)
    )
    if not lyricist.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    # 准备数据
    sample_data = data.model_dump()
    if sample_data.get("tags"):
        sample_data["tags"] = json.dumps(sample_data["tags"], ensure_ascii=False)
    
    sample = LyricsSample(**sample_data)
    db.add(sample)
    await db.flush()
    await db.refresh(sample)
    
    return SampleResponse(
        **sample.__dict__,
        tags=data.tags or [],
        lyricist_name=lyricist.scalar_one().name
    )


@router.post("/batch", response_model=MessageResponse)
async def batch_create_samples(
    samples: List[SampleCreate],
    db: AsyncSession = Depends(get_db)
):
    """批量创建歌词样本"""
    created = 0
    errors = []
    
    for sample_data in samples:
        try:
            # 检查作词人
            lyricist = await db.execute(
                select(Lyricist).where(Lyricist.id == sample_data.lyricist_id)
            )
            if not lyricist.scalar_one_or_none():
                errors.append(f"作词人 {sample_data.lyricist_id} 不存在")
                continue
            
            data = sample_data.model_dump()
            if data.get("tags"):
                data["tags"] = json.dumps(data["tags"], ensure_ascii=False)
            
            sample = LyricsSample(**data)
            db.add(sample)
            created += 1
        except Exception as e:
            errors.append(str(e))
    
    return MessageResponse(
        message=f"成功创建 {created} 条样本",
        success=len(errors) == 0
    )


@router.get("/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取歌词样本详情"""
    result = await db.execute(
        select(LyricsSample).where(LyricsSample.id == sample_id)
    )
    sample = result.scalar_one_or_none()
    
    if not sample:
        raise HTTPException(status_code=404, detail="样本不存在")
    
    lyricist = await db.execute(
        select(Lyricist.name).where(Lyricist.id == sample.lyricist_id)
    )
    lyricist_name = lyricist.scalar()
    
    return SampleResponse(
        **sample.__dict__,
        tags=json.loads(sample.tags) if sample.tags else [],
        lyricist_name=lyricist_name
    )


@router.put("/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: int,
    data: SampleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新歌词样本"""
    result = await db.execute(
        select(LyricsSample).where(LyricsSample.id == sample_id)
    )
    sample = result.scalar_one_or_none()
    
    if not sample:
        raise HTTPException(status_code=404, detail="样本不存在")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("tags"):
        update_data["tags"] = json.dumps(update_data["tags"], ensure_ascii=False)
    
    for key, value in update_data.items():
        setattr(sample, key, value)
    
    await db.flush()
    await db.refresh(sample)
    
    lyricist = await db.execute(
        select(Lyricist.name).where(Lyricist.id == sample.lyricist_id)
    )
    lyricist_name = lyricist.scalar()
    
    return SampleResponse(
        **sample.__dict__,
        tags=json.loads(sample.tags) if sample.tags else [],
        lyricist_name=lyricist_name
    )


@router.delete("/{sample_id}", response_model=MessageResponse)
async def delete_sample(
    sample_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除歌词样本"""
    result = await db.execute(
        select(LyricsSample).where(LyricsSample.id == sample_id)
    )
    sample = result.scalar_one_or_none()
    
    if not sample:
        raise HTTPException(status_code=404, detail="样本不存在")
    
    await db.delete(sample)
    
    return MessageResponse(message="删除成功")


@router.post("/import", response_model=MessageResponse)
async def import_samples(
    lyricist_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """导入歌词样本（支持 TXT/JSON/CSV）"""
    # 检查作词人
    lyricist = await db.execute(
        select(Lyricist).where(Lyricist.id == lyricist_id)
    )
    if not lyricist.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="作词人不存在")
    
    content = await file.read()
    filename = file.filename.lower()
    created = 0
    
    try:
        if filename.endswith(".json"):
            # JSON 格式：[{ "title": "", "content": "", ... }]
            data = json.loads(content.decode("utf-8"))
            for item in data:
                sample = LyricsSample(
                    lyricist_id=lyricist_id,
                    title=item.get("title"),
                    content=item.get("content", ""),
                    source=item.get("source"),
                    tags=json.dumps(item.get("tags", []), ensure_ascii=False)
                )
                db.add(sample)
                created += 1
                
        elif filename.endswith(".csv"):
            # CSV 格式：title,content,source
            lines = content.decode("utf-8").strip().split("\n")
            for line in lines[1:]:  # 跳过表头
                parts = line.split(",", 2)
                if len(parts) >= 2:
                    sample = LyricsSample(
                        lyricist_id=lyricist_id,
                        title=parts[0].strip(),
                        content=parts[1].strip(),
                        source=parts[2].strip() if len(parts) > 2 else None
                    )
                    db.add(sample)
                    created += 1
                    
        else:
            # TXT 格式：用空行分隔不同歌曲
            text = content.decode("utf-8")
            songs = text.split("\n\n")
            for song in songs:
                song = song.strip()
                if song:
                    lines = song.split("\n")
                    title = lines[0].strip() if lines else None
                    content_text = "\n".join(lines[1:]) if len(lines) > 1 else song
                    
                    sample = LyricsSample(
                        lyricist_id=lyricist_id,
                        title=title,
                        content=content_text
                    )
                    db.add(sample)
                    created += 1
        
        return MessageResponse(message=f"成功导入 {created} 条样本")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")
