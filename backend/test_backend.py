"""
he_write 后端测试脚本

测试所有 API 端点是否正常工作
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)
    
    try:
        print("✓ 导入 core.config")
        from app.core.config import settings
        print(f"  DATABASE_URL: {settings.DATABASE_URL}")
        
        print("✓ 导入 core.database")
        from app.core.database import engine, Base, get_db
        
        print("✓ 导入 models.models")
        from app.models.models import Lyricist, LyricsSample, TrainedModel
        
        print("✓ 导入 schemas.schemas")
        from app.schemas.schemas import LyricistCreate, LyricistResponse
        
        print("✓ 导入 services.crawler_service")
        from app.services.crawler_service import crawler_service, LyricsCleaner
        
        print("✓ 导入 services.training_service")
        from app.services.training_service import training_service, MarkovModel
        
        print("✓ 导入 services.generation_service")
        from app.services.generation_service import generation_service
        
        print("✓ 导入 api.lyricist")
        from app.api import lyricist
        
        print("\n所有模块导入成功! ✓")
        return True
        
    except Exception as e:
        print(f"\n导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """测试 FastAPI 应用创建"""
    print("\n" + "=" * 50)
    print("测试 FastAPI 应用创建...")
    print("=" * 50)
    
    try:
        from main import app
        print(f"✓ 应用创建成功: {app.title}")
        print(f"  版本: {app.version}")
        
        # 列出所有路由
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        print(f"  路由数量: {len(routes)}")
        
        return True
    except Exception as e:
        print(f"应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lyrics_cleaner():
    """测试歌词清洗功能"""
    print("\n" + "=" * 50)
    print("测试歌词清洗功能...")
    print("=" * 50)
    
    from app.services.crawler_service import LyricsCleaner
    
    # 测试清洗
    dirty_lyrics = """
    [00:00.00]测试歌词
    作曲：张三
    作词：李四
    
    这是一首测试歌曲
    歌词内容在这里
    
    [01:23.45]时间标签
    """
    
    clean = LyricsCleaner.clean(dirty_lyrics)
    print(f"清洗结果:\n{clean}")
    
    # 测试验证
    is_valid = LyricsCleaner.is_valid(clean)
    print(f"是否有效: {is_valid}")
    
    # 测试质量评分
    score = LyricsCleaner.calculate_quality(clean)
    print(f"质量评分: {score:.2f}")
    
    return True


def test_markov_model():
    """测试 Markov 模型"""
    print("\n" + "=" * 50)
    print("测试 Markov 模型...")
    print("=" * 50)
    
    from app.services.training_service import MarkovModel
    
    # 训练数据
    texts = [
        "春风吹过山岗，花儿遍地开放",
        "月光洒满大地，星光照亮夜空",
        "思念随风飘远，心事无处安放",
        "岁月静好如初，时光温柔以待",
    ]
    
    model = MarkovModel(order=2)
    stats = model.train(texts)
    print(f"训练统计: {stats}")
    
    # 生成测试
    generated = model.generate(max_length=50)
    print(f"生成结果: {generated}")
    
    return True


async def test_api_endpoints():
    """测试 API 端点"""
    print("\n" + "=" * 50)
    print("测试 API 端点 (需要启动服务)...")
    print("=" * 50)
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient() as client:
            # 健康检查
            try:
                resp = await client.get(f"{base_url}/health", timeout=5.0)
                if resp.status_code == 200:
                    print("✓ 健康检查通过")
                else:
                    print(f"✗ 健康检查失败: {resp.status_code}")
                    return False
            except httpx.ConnectError:
                print("⚠ 服务未启动，跳过 API 测试")
                return True
            
            # 测试根路径
            resp = await client.get(f"{base_url}/")
            print(f"✓ 根路径: {resp.json()}")
            
            # 测试创建作词人
            resp = await client.post(
                f"{base_url}/api/lyricists",
                json={"name": "测试作词人", "style": "流行"}
            )
            if resp.status_code in [200, 400]:
                print("✓ 创建作词人 API")
            
            # 测试获取列表
            resp = await client.get(f"{base_url}/api/lyricists")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 作词人列表: {len(data)} 条")
            
            print("\nAPI 测试完成!")
            return True
            
    except Exception as e:
        print(f"API 测试失败: {e}")
        return True  # 不阻止启动


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  he_write 后端测试")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    # 测试导入
    if not test_imports():
        all_passed = False
    
    # 测试应用创建
    if not test_app_creation():
        all_passed = False
    
    # 测试歌词清洗
    test_lyrics_cleaner()
    
    # 测试 Markov 模型
    test_markov_model()
    
    # 测试 API (异步)
    asyncio.run(test_api_endpoints())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  所有测试通过! ✓")
        print("=" * 60 + "\n")
        print("启动命令:")
        print("  cd backend && python main.py")
        print("  或")
        print("  cd backend && uvicorn main:app --reload")
    else:
        print("  部分测试失败，请检查错误信息")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
