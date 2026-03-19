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
        # 模拟歌词数据模板
        mock_templates = [
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
            },
            {
                "title": "秋叶飘零",
                "content": """秋叶飘落在风中
像是对过往的告别
金黄色的记忆
在阳光下闪耀

曾经青葱的岁月
如今已化作落叶
飘向远方的土地
滋养着新的希望

时光轮回四季更迭
生命总有离别重逢
珍惜当下每一刻
让美好永驻心间""",
                "year": 2020
            },
            {
                "title": "冬日暖阳",
                "content": """冬日暖阳照进窗
驱散了寒冷的冰霜
一杯热茶在手中
温暖整个心房

窗外的雪花飘落
世界银装素裹
安静祥和的美好
让人心生向往

无论多冷的冬天
总有温暖的期待
春天终将到来
花儿终会盛开""",
                "year": 2022
            },
            {
                "title": "海浪声声",
                "content": """海浪声声拍打岸边
带来大海的呼唤
海风吹过脸庞
带走所有的烦忧

蓝天白云映照海面
海鸥自由翱翔
此刻世界如此宽广
心胸也被打开

站在海边眺望远方
未来的路还很长
带着勇气向前走
追逐心中的梦想""",
                "year": 2021
            },
            {
                "title": "山间小路",
                "content": """走在山间的小路上
两旁绿树成荫
鸟儿在枝头歌唱
蝴蝶在花间飞舞

溪水潺潺流淌
清澈见底
大自然的美景
让人心旷神怡

放慢脚步感受当下
远离城市的喧嚣
在这宁静的山间
找到内心的平和""",
                "year": 2023
            },
            {
                "title": "花开时节",
                "content": """春天花开满枝头
桃红柳绿醉人心
蜜蜂蝴蝶翩翩舞
花香四溢满园春

花开花落总有时
珍惜眼前美好景
莫待花落空叹息
春光易逝不等人

愿你的生命如花
绽放最美的色彩
在属于你的季节里
尽情展现芬芳""",
                "year": 2020
            },
            {
                "title": "夜深人静",
                "content": """夜深人静时
思绪悄然升起
往事如电影
一幕幕在脑海播放

那些错过的机会
那些未能说的话
都在这寂静的夜里
化作深深的叹息

但明天太阳依然升起
新的希望在前方等待
把遗憾留在昨天
勇敢迎接新的一天""",
                "year": 2021
            },
            {
                "title": "故乡的云",
                "content": """故乡的云啊飘向何方
是否也像我一样流浪
离开家乡的游子
心中装着思念的行囊

故乡的水故乡的山
故乡的人故乡的情
无论走多远
心中总有牵挂

愿故乡的云为我带去问候
告诉家人我安好
总有一天我会回来
回到那个温暖的地方""",
                "year": 2019
            },
            {
                "title": "城市霓虹",
                "content": """城市霓虹闪烁
照亮夜的天空
车水马龙的街道
永不停息的节奏

在这繁华的都市
每个人都在奔波
为了梦想和生活
努力向前不停歇

城市的夜晚不眠
希望每个人都能找到
属于自己的那盏灯
照亮前行的路""",
                "year": 2022
            },
            {
                "title": "友情岁月",
                "content": """那些年我们并肩同行
一起欢笑一起哭泣
友情岁月如此珍贵
铭记于心永不忘记

朋友是人生路上的光
照亮黑暗的时刻
朋友是寒冬里的火
温暖冰冷的心房

愿我们的友情长存
跨越时间的距离
无论何时何地
都是彼此的依靠""",
                "year": 2020
            },
            {
                "title": "梦想起航",
                "content": """梦想是一艘船
载着我们驶向远方
无论风浪多大
都不要放弃希望

扬起信念的帆
握紧努力的桨
在人生的海洋
书写自己的传奇

梦想不分大小
只要坚持就有意义
让梦想起航
去追逐那片天""",
                "year": 2023
            },
            {
                "title": "雨后彩虹",
                "content": """风雨过后见彩虹
生活总有起伏跌宕
不要被困难打败
坚持就会看到希望

彩虹再美也短暂
但它给人无限憧憬
就像生活中的美好
值得我们去追寻

愿每个人的人生
都能在风雨后
遇见属于自己的彩虹
绚丽多彩灿烂辉煌""",
                "year": 2021
            },
            {
                "title": "心中的歌",
                "content": """心中有一首歌
唱给自己的灵魂
关于梦想关于爱
关于生活的真谛

这首歌没有华丽的词藻
却是最真实的表达
每一个音符
都是生命的痕迹

愿心中的歌永远唱响
不管外界如何喧嚣
保持内心的纯净
做最真实的自己""",
                "year": 2022
            },
            {
                "title": "时光倒流",
                "content": """如果时光能够倒流
我会更加珍惜每一刻
把握住那些美好
不让它们从指间溜走

但时光不会倒流
过去已经无法改变
唯有把握现在
创造更好的未来

带着过去的教训
珍惜现在的时光
期待明天的太阳
让生命更加精彩""",
                "year": 2020
            },
            {
                "title": "落叶归根",
                "content": """落叶归根是宿命
无论飘向何方
最终都要回到起点
生命如此循环

我们像漂泊的叶子
在人生的风中飘荡
寻找着属于自己的归宿
那片安静的土壤

愿每个流浪的灵魂
都能找到家的方向
在生命的终点
回归最初的安宁""",
                "year": 2019
            },
            {
                "title": "心灵的港湾",
                "content": """每个人都需要一个港湾
停泊疲惫的心灵
卸下生活的重担
找回内心的宁静

港湾不一定要华丽
只要能让人安心
在风雨来临时
给予温暖的庇护

愿你找到自己的港湾
在人生的旅途中
有一个可以休憩的地方
重新积蓄前行的力量""",
                "year": 2021
            },
            {
                "title": "追风筝的人",
                "content": """仰望天空中的风筝
自由自在地飞翔
牵着那根细细的线
追着风的方向跑

风筝在天空中舞蹈
像是一个美丽的梦
我们都是追风筝的人
追逐着自己的理想

愿你的风筝永远高飞
在人生的天空中
画出最美的弧线
成为最亮的那颗星""",
                "year": 2022
            },
            {
                "title": "温暖的拥抱",
                "content": """一个温暖的拥抱
胜过千言万语
传递着爱与关怀
温暖冰冷的心房

当你感到孤独时
多么需要这样的温暖
让你知道你并不孤单
有人在默默关心着你

愿每个人都能给予
也都能收到这样的温暖
让世界因为拥抱
变得更加美好""",
                "year": 2023
            },
            {
                "title": "星空下的约定",
                "content": """在那片星空下
我们许下约定
不管未来怎样
都要勇敢地走下去

星星见证了我们的诺言
月亮听到了我们的心愿
这份珍贵的约定
铭刻在心永不改变

愿星空下的约定
成为前进的动力
无论遇到什么困难
都不要放弃最初的梦想""",
                "year": 2020
            },
            {
                "title": "心中的那片海",
                "content": """心中有一片海
宽阔而深邃
容纳所有的喜怒哀乐
包容一切的风浪

这片海是我的秘密花园
在这我可以自由地呼吸
做最真实的自己
不被外界打扰

愿每个人心中都有一片海
能够容纳生命的起伏
在风雨中保持平静
在阳光下闪闪发光""",
                "year": 2021
            },
            {
                "title": "岁月如诗",
                "content": """岁月如诗
缓缓流淌
每一个日子
都是一行诗句

有欢笑有泪水
有相聚有离别
这些都是诗的韵律
谱写着生命的篇章

愿你的岁月如诗
优美而动人
在时间的长河中
留下最美的痕迹""",
                "year": 2022
            },
            {
                "title": "梦中的花园",
                "content": """在梦中我看见一座花园
繁花似锦美不胜收
蝴蝶翩翩蜜蜂嗡嗡
阳光温暖微风轻柔

这是我心中的理想国
一个没有忧愁的地方
我可以自由地呼吸
享受生命的美好

愿梦中的花园
终有一天成为现实
在你的生活中绽放
带给你无尽的欢乐""",
                "year": 2023
            },
            {
                "title": "穿越时光",
                "content": """如果可以穿越时光
我想回到那个夏天
重温那些美好时光
再次感受那份悸动

但时光不可逆转
过去只能成为回忆
珍藏于心永远怀念
带着它继续前行

穿越时光是一场梦
但未来是可以创造的
让我们把握现在
书写新的故事""",
                "year": 2019
            },
            {
                "title": "生命的河流",
                "content": """生命是一条河流
从源头流向大海
沿途经历风雨
见证无数风景

有平静的水面
也有湍急的激流
无论遇到什么
都勇往直前

愿你的生命河流
奔腾不息壮丽磅礴
最终汇入那片海
成为永恒的存在""",
                "year": 2020
            },
            {
                "title": "心中的明灯",
                "content": """心中的明灯
照亮前行的路
在黑暗中指引方向
给人勇气和希望

这盏灯是信念
是对未来的期待
无论多么困难
都不要让它熄灭

愿心中的明灯
永远闪烁不灭
照亮你的人生之路
引领你走向光明""",
                "year": 2021
            },
            {
                "title": "春暖花开",
                "content": """春暖花开的时节
万物复苏生机盎然
小草钻出泥土
花儿绽放笑脸

春风吹过山岗
带来泥土的芬芳
阳光洒向大地
温暖每个角落

愿你的生活如春天
充满希望和活力
每一天都是新的开始
每一步都走向美好""",
                "year": 2022
            },
            {
                "title": "深秋的思念",
                "content": """深秋的思念
如落叶般飘零
每一片都是回忆
承载着无尽的牵挂

秋风萧瑟的季节
思绪随风飘向远方
带到思念的人身边
传递着我的问候

愿这份思念
能够穿越时空
在彼此的心中
种下温暖的种子""",
                "year": 2023
            },
            {
                "title": "夜空的星",
                "content": """夜空中闪烁的星
像是无数的眼睛
默默注视着大地
守护着每个梦想

仰望星空的那一刻
烦恼都变得渺小
宇宙如此浩瀚
我们都是其中的一粒尘埃

愿每颗星都能找到
属于自己的位置
在浩瀚的宇宙中
发出属于自己的光芒""",
                "year": 2020
            },
            {
                "title": "生命的意义",
                "content": """生命的意义是什么
每个人都有不同答案
有人追求名利
有人追求梦想

意义不在于达到什么
而在于追寻的过程
每一步走过的路
都是生命的印记

愿你找到生命的意义
活出自己想要的样子
不留遗憾不虚此生
让每一天都值得""",
                "year": 2021
            },
            {
                "title": "永不停歇",
                "content": """时间的脚步永不停歇
从清晨到黄昏
从春夏到秋冬
生命在一刻不停地流淌

我们不能阻挡时间
但可以让每一刻都有意义
珍惜当下把握机会
让生命绽放光彩

愿你的脚步永不停歇
在人生的道路上
留下深深的足迹
创造属于自己的传奇""",
                "year": 2022
            },
            {
                "title": "内心的声音",
                "content": """听内心深处的声音
它在告诉你什么
是梦想是渴望
还是被忽略的呼唤

外界太喧嚣
我们常常迷失自己
忘记最初的方向
忘记为什么出发

愿你能听到内心的声音
勇敢地追随它
找到真正的自己
活出精彩的人生""",
                "year": 2023
            },
            {
                "title": "缘起缘落",
                "content": """人与人之间的相遇
都是一种缘分
有的成为朋友
有的成为过客

缘起时珍惜
缘落时释怀
每一段经历
都是生命的礼物

愿你珍惜每一份缘
感恩每一次相遇
无论结局如何
都成为美好的回忆""",
                "year": 2019
            },
            {
                "title": "生命如歌",
                "content": """生命如歌
有高潮有低谷
有欢快有忧伤
共同谱写人生的旋律

每一个音符都很重要
缺一不可
正是这些起伏跌宕
让歌曲变得动人

愿你的生命之歌
美妙动听
在每个音符中
都能找到意义和快乐""",
                "year": 2020
            },
            {
                "title": "前行的力量",
                "content": """是什么让你坚持
是什么给你勇气
是梦想是爱
还是内心的那份执着

前行的路上
总会有风雨坎坷
但只要心中有光
就不会迷失方向

愿你拥有前行的力量
勇敢面对一切挑战
在人生的旅途中
成为更好的自己""",
                "year": 2021
            },
            {
                "title": "美好的相遇",
                "content": """美好的相遇
是生命中最珍贵的礼物
让平淡的日子
变得精彩纷呈

一次偶然的邂逅
可能改变一生
一个真诚的微笑
可能温暖一颗心

愿你的生命中
充满美好的相遇
每一段缘分
都成为珍贵的回忆""",
                "year": 2022
            },
            {
                "title": "永不放弃",
                "content": """当困难来临时
不要轻言放弃
坚持就是胜利
黑暗终将过去

每一次跌倒
都是为了更好地站起来
每一次失败
都是通向成功的台阶

愿你永不放弃
勇敢地追逐梦想
在人生的舞台上
绽放最耀眼的光芒""",
                "year": 2023
            },
            {
                "title": "心中的天使",
                "content": """每个人心中都有一位天使
守护着那份纯真和善良
在最黑暗的时刻
给予温暖和希望

这位天使是善良的自己
是对美好的向往
是对生命的热爱
是对梦想的坚持

愿你心中的天使
永远守护着你
引导你走向光明
让你的人生充满爱与希望""",
                "year": 2020
            },
            {
                "title": "生命之树",
                "content": """生命如同一棵树
从种子到大树
经历风雨的洗礼
在时间的长河中成长

根深才能叶茂
经历才能沉淀
每一次的磨难
都是生命的养分

愿你的生命之树
枝繁叶茂根深蒂固
在岁月的风雨中
绽放最美的姿态""",
                "year": 2021
            },
            {
                "title": "勇敢的心",
                "content": """一颗勇敢的心
敢于面对未知
敢于接受挑战
敢于追逐梦想

勇气不是没有恐惧
而是克服恐惧继续前行
每一步都需要勇气
每一次突破都是成长

愿你拥有一颗勇敢的心
无所畏惧地生活
在人生的旅途中
创造属于自己的奇迹""",
                "year": 2022
            },
            {
                "title": "生命的礼赞",
                "content": """生命是一场奇妙的旅程
有开始也有结束
有欢乐也有悲伤
每一刻都值得珍惜

感恩生命中的每一次遇见
感恩生命中的每一份温暖
是这些构成了我们
让生命变得丰富多彩

愿你的生命
如同一首优美的诗
一幅绚丽的画
值得被铭记被礼赞""",
                "year": 2023
            },
            {
                "title": "永恒的希望",
                "content": """希望是一盏灯
照亮黑暗的夜
希望是一把钥匙
打开困住的门

只要有希望在
就有无限的可能
不要让希望熄灭
它是生命中最宝贵的财富

愿希望永远陪伴着你
在人生的每个阶段
都给予你力量和勇气
让你的人生充满光明""",
                "year": 2019
            }
        ]
        
        results = []
        for i, item in enumerate(mock_lyrics[:max_samples]):
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
        await asyncio.sleep(0.1)
        
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
