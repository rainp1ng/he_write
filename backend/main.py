"""
he_write 后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.api import lyricist, sample, model, generation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时清理资源
    await engine.dispose()


app = FastAPI(
    title="he_write API",
    description="作词人训练系统 API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(lyricist.router, prefix="/api/lyricists", tags=["lyricists"])
app.include_router(sample.router, prefix="/api/samples", tags=["samples"])
app.include_router(model.router, prefix="/api/models", tags=["models"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "he_write API is running"}


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
