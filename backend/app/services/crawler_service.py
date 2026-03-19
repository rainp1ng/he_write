"""
歌词爬虫服务

支持多数据源歌词采集，包括网易云、QQ音乐等。
MVP 版本使用模拟数据，实际生产环境需要处理反爬机制。
"""
import asyncio
import random
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

import httpx
from bs4 import BeautifulSoup
from loguru import logger


@dataclass
class CrawlResult:
    """爬取结果"""
    title: str
    content: str
    source: str
    source_url: Optional[str] = None
    year: Optional[int] = None
    quality_score: float = 0.8


@dataclass
class CrawlProgress:
    """爬取进度"""
    status: str = "idle"  # idle, running, completed, failed
    found: int = 0
    saved: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class LyricsCleaner:
    """歌词清洗工具"""
    
    # 需要过滤的模式
    NOISE_PATTERNS = [
        r'\[.*?\]',           # [00:00.00] 时间标签
        r'作曲[：:]\s*.*?\n',  # 作曲信息
        r'编曲[：:]\s*.*?\n',  # 编曲信息
        r'演唱[：:]\s*.*?\n',  # 演唱信息
        r'专辑[：:]\s*.*?\n',  # 专辑信息
        r'\n{3,}',           # 多个空行
        r'^\s+|\s+$',        # 首尾空白
    ]
    
    @classmethod
    def clean(cls, content: str) -> str:
        """清洗歌词内容"""
        if not content:
            return ""
        
        # 去除噪音
        for pattern in cls.NOISE_PATTERNS:
            content = re.sub(pattern, '\n', content, flags=re.MULTILINE)
        
        # 标准化换行
        content = content.strip()
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        return '\n'.join(lines)
    
    @classmethod
    def is_valid(cls, content: str, min_length: int = 50) -> bool:
        """检查歌词是否有效"""
        if not content or len(content) < min_length:
            return False
        
        # 检查是否有足够的内容
        lines = [l for l in content.split('\n') if l.strip()]
        if len(lines) < 4:  # 至少4行
            return False
        
        # 检查是否是纯英文/数字（可能是无效内容）
        chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
        if chinese_chars / len(content) < 0.3:  # 中文占比至少30%
            return False
        
        return True
    
    @classmethod
    def calculate_quality(cls, content: str) -> float:
        """计算歌词质量分数 (0-1)"""
        if not content:
            return 0.0
        
        score = 0.5  # 基础分
        
        # 长度加分
        length = len(content)
        if length > 200:
            score += 0.1
        if length > 500:
            score += 0.1
        
        # 结构加分（有段落分隔）
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 2:
            score += 0.1
        
        # 中文占比加分
        chinese_ratio = sum(1 for c in content if '\u4e00' <= c <= '\u9fff') / len(content)
        if chinese_ratio > 0.6:
            score += 0.1
        
        # 去除重复行加分
        lines = content.split('\n')
        unique_lines = set(lines)
        if len(unique_lines) / len(lines) > 0.7:
            score += 0.1
        
        return min(score, 1.0)


class LyricCrawler:
    """歌词爬虫"""
    
    def __init__(self, delay: float = 1.0, timeout: int = 30):
        self.delay = delay
        self.timeout = timeout
        self.progress = CrawlProgress()
        self._stop_flag = False
        
        # User-Agent 池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
    
    def get_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    async def search_lyrics(
        self, 
        lyricist_name: str,
        sources: List[str] = None,
        max_samples: int = 50
    ) -> List[CrawlResult]:
        """
        搜索作词人的歌词
        
        Args:
            lyricist_name: 作词人姓名
            sources: 数据源列表 (netease, qq, kugou)
            max_samples: 最大采集数量
        
        Returns:
            爬取结果列表
        """
        self.progress = CrawlProgress(status="running")
        self._stop_flag = False
        
        if sources is None:
            sources = ["netease"]
        
        results = []
        seen_hashes = set()  # 用于去重
        
        for source in sources:
            if self._stop_flag:
                break
                
            try:
                logger.info(f"开始从 {source} 搜索: {lyricist_name}")
                
                if source == "netease":
                    items = await self._crawl_netease(lyricist_name, max_samples)
                elif source == "qq":
                    items = await self._crawl_qq(lyricist_name, max_samples)
                elif source == "mock":
                    items = await self._crawl_mock(lyricist_name, max_samples)
                else:
                    logger.warning(f"不支持的数据源: {source}")
                    continue
                
                # 去重并添加结果
                for item in items:
                    content_hash = hashlib.md5(item.content.encode()).hexdigest()
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        results.append(item)
                        self.progress.found += 1
                
                logger.info(f"{source} 完成，找到 {len(items)} 条")
                
            except Exception as e:
                error_msg = f"{source} 爬取失败: {str(e)}"
                logger.error(error_msg)
                self.progress.errors.append(error_msg)
            
            await asyncio.sleep(self.delay)
        
        self.progress.status = "completed"
        self.progress.saved = len(results)
        
        return results[:max_samples]
    
    async def _crawl_netease(self, name: str, max_samples: int) -> List[CrawlResult]:
        """
        网易云音乐爬虫
        
        注意：实际爬取需要处理加密参数，这里使用模拟数据
        """
        # MVP 阶段：返回模拟数据
        # 实际实现需要：
        # 1. 搜索 API: https://music.163.com/api/search/get
        # 2. 歌词 API: https://music.163.com/api/song/lyric
        # 3. 处理加密参数和反爬机制
        
        logger.info(f"[网易云] 使用模拟数据 (MVP模式)")
        return await self._crawl_mock(name, max_samples)
    
    async def _crawl_qq(self, name: str, max_samples: int) -> List[CrawlResult]:
        """
        QQ音乐爬虫
        
        注意：实际爬取需要处理加密参数，这里使用模拟数据
        """
        # MVP 阶段：返回模拟数据
        logger.info(f"[QQ音乐] 使用模拟数据 (MVP模式)")
        return await self._crawl_mock(name, max_samples)
    
    async def _crawl_mock(self, name: str, max_samples: int) -> List[CrawlResult]:
        """
        模拟爬虫 - 用于测试和 MVP 演示
        
        返回模拟的歌词数据
        """
        # 模拟歌词数据
        mock_lyrics = [
            {
                "title": "春风十里",
                "content": """春风十里不如你
我在等风也在等你
桃花开了又落了
时光匆匆流去了

那些年我们一起走过
那些梦我们一起做过
春风吹过你的脸庞
我的心里依然滚烫

岁月静好现世安稳
有你的日子都是春天
不需要太多承诺
只要你在身边就好""",
                "year": 2020
            },
            {
                "title": "月光下的故事",
                "content": """月光洒在窗台上
思念悄悄爬上心房
远方的你是否也在看
这同一轮明月光

风吹过树叶沙沙响
像是你的声音在耳边
那些未说完的话语
都化作点点星光

月有阴晴圆缺
人有悲欢离合
但愿人长久
千里共婵娟""",
                "year": 2021
            },
            {
                "title": "雨中的回忆",
                "content": """窗外下着小雨
滴答滴答敲打玻璃
想起那个雨天的遇见
从此你住进我的心里

雨伞下的世界
只有你和我
雨滴奏响爱的旋律
编织我们的故事

多年以后再听雨
依然能想起你的笑颜
那些美好时光
藏在记忆的深处""",
                "year": 2019
            },
            {
                "title": "星河璀璨",
                "content": """夜空中最亮的星
能否听清
那仰望的人
心底的孤独和叹息

夜空中最亮的星
能否记起
曾与我同行
消失在风里的身影

我祈祷拥有一颗透明的心灵
和会流泪的眼睛
给我再去相信的勇气
越过谎言去拥抱你""",
                "year": 2022
            },
            {
                "title": "青春纪念册",
                "content": """翻开那本泛黄的相册
青春的脸庞依然清晰
那些笑声和泪水
都是最珍贵的回忆

教室里的书声琅琅
操场上的奔跑欢畅
课桌上刻下的名字
是青春最美的印记

时光匆匆不停留
青春一去不复返
但那些美好的瞬间
永远定格在心间""",
                "year": 2023
            },
            {
                "title": "岁月的歌",
                "content": """岁月如歌轻轻唱
唱尽人间悲欢离合
花开花落年复年
时光匆匆不留痕

曾经年少轻狂时
总以为来日方长
如今回望来时路
方知岁月最无情

愿时光能缓
愿故人不散
愿你惦念的人能和你道晚安
愿你独闯的日子里不觉得孤单""",
                "year": 2020
            },
            {
                "title": "远方的你",
                "content": """远方的你还好吗
是否也会偶尔想起
那些共同度过的日子
那些青春里的故事

山高水长阻隔不断
我对你的思念
愿你一切安好
愿你笑颜如花

无论相隔多远
心总能找到方向
因为有你
生活充满希望""",
                "year": 2021
            },
            {
                "title": "晨光微熹",
                "content": """晨光微熹透进窗
新的一天悄然来
昨夜的梦已远去
新的希望在前方

阳光洒在脸庞
温暖流淌心间
生活或许平淡
但依然有光芒

珍惜每一个清晨
拥抱每一个开始
让生命充满力量
让梦想照进现实""",
                "year": 2022
            },
            {
                "title": "时光信笺",
                "content": """写一封给未来的信
寄托我的愿望和期盼
希望那时的你
依然记得今天的自己

时光是最公正的裁判
见证每一份努力
岁月是最温柔的朋友
收藏每一份真心

愿你成为想成为的人
愿所有的期待都能实现
愿时光不负有心人
愿岁月善待你我""",
                "year": 2023
            },
            {
                "title": "晚风轻语",
                "content": """晚风轻轻吹过
带来夜的温柔
星星点点闪烁
照亮归家的路

卸下一身疲惫
在夜色中漫步
听风儿轻声细语
诉说白天的故事

夜深人静时
心灵最是安宁
让所有的烦恼
都随风飘远""",
                "year": 2021
            }
        ]
        
        results = []
        for item in mock_lyrics[:max_samples]:
            content = LyricsCleaner.clean(item["content"])
            if LyricsCleaner.is_valid(content):
                results.append(CrawlResult(
                    title=f"{name} - {item['title']}",
                    content=content,
                    source="mock",
                    source_url=None,
                    year=item.get("year"),
                    quality_score=LyricsCleaner.calculate_quality(content)
                ))
        
        # 模拟网络延迟
        await asyncio.sleep(0.5)
        
        return results
    
    def stop(self):
        """停止爬取"""
        self._stop_flag = True
        self.progress.status = "stopped"


class CrawlerService:
    """爬虫服务 - 对外接口"""
    
    def __init__(self):
        self._crawlers: Dict[int, LyricCrawler] = {}
    
    async def crawl_lyricist(
        self,
        lyricist_id: int,
        lyricist_name: str,
        sources: List[str] = None,
        max_samples: int = 50
    ) -> Tuple[List[CrawlResult], CrawlProgress]:
        """
        爬取作词人歌词
        
        Args:
            lyricist_id: 作词人ID
            lyricist_name: 作词人姓名
            sources: 数据源
            max_samples: 最大采集数量
        
        Returns:
            (爬取结果列表, 爬取进度)
        """
        crawler = LyricCrawler()
        self._crawlers[lyricist_id] = crawler
        
        try:
            results = await crawler.search_lyrics(
                lyricist_name, 
                sources=sources,
                max_samples=max_samples
            )
            return results, crawler.progress
        finally:
            if lyricist_id in self._crawlers:
                del self._crawlers[lyricist_id]
    
    def stop_crawl(self, lyricist_id: int):
        """停止爬取"""
        if lyricist_id in self._crawlers:
            self._crawlers[lyricist_id].stop()
    
    def get_progress(self, lyricist_id: int) -> Optional[CrawlProgress]:
        """获取爬取进度"""
        if lyricist_id in self._crawlers:
            return self._crawlers[lyricist_id].progress
        return None


# 单例服务
crawler_service = CrawlerService()
