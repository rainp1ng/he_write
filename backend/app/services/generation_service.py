"""
歌词生成服务

支持多种生成模式，MVP 阶段使用统计模型生成，
生产环境可加载 GPT-2 / Qwen 等深度学习模型。
"""
import asyncio
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from loguru import logger

from app.services.training_service import MarkovModel, NGramModel, training_service


@dataclass
class GenerationConfig:
    """生成配置"""
    temperature: float = 0.9       # 创意度 (0.1 - 2.0)
    top_p: float = 0.95            # 核采样
    top_k: int = 50                # Top-K 采样
    max_length: int = 256          # 最大生成长度
    repetition_penalty: float = 1.2  # 重复惩罚
    min_length: int = 50           # 最小生成长度


@dataclass
class GenerationResult:
    """生成结果"""
    text: str
    mode: str
    config: GenerationConfig
    model_id: int
    created_at: datetime = field(default_factory=datetime.now)


class LyricsPostProcessor:
    """歌词后处理器"""
    
    @staticmethod
    def format_lyrics(text: str, style: str = "default") -> str:
        """
        格式化歌词
        
        Args:
            text: 原始文本
            style: 格式化风格
        
        Returns:
            格式化后的歌词
        """
        if not text:
            return ""
        
        # 去除多余空白
        text = text.strip()
        
        # 按标点分割成行
        lines = re.split(r'([，。！？、；])', text)
        
        # 重新组合
        formatted_lines = []
        current_line = ""
        
        for part in lines:
            if part in ['，', '。', '！', '？', '、', '；']:
                current_line += part
                if part in ['。', '！', '？']:
                    formatted_lines.append(current_line)
                    current_line = ""
            else:
                # 每隔7-10个字换行（歌词常用格式）
                if len(current_line) >= 7 and current_line:
                    formatted_lines.append(current_line)
                    current_line = part
                else:
                    current_line += part
        
        if current_line:
            formatted_lines.append(current_line)
        
        # 两行为一段
        paragraphs = []
        for i in range(0, len(formatted_lines), 2):
            para = '\n'.join(formatted_lines[i:i+2])
            paragraphs.append(para)
        
        return '\n\n'.join(paragraphs)
    
    @staticmethod
    def remove_repetition(text: str, max_repeat: int = 3) -> str:
        """
        去除过度重复的内容
        
        Args:
            text: 原始文本
            max_repeat: 最大重复次数
        
        Returns:
            处理后的文本
        """
        lines = text.split('\n')
        result = []
        line_count = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            count = line_count.get(line, 0)
            if count < max_repeat:
                result.append(line)
                line_count[line] = count + 1
        
        return '\n'.join(result)
    
    @staticmethod
    def add_structure(text: str) -> str:
        """
        添加歌曲结构标记
        
        Returns:
            带结构标记的歌词
        """
        lines = text.split('\n\n')
        
        if len(lines) >= 2:
            # 标记主歌和副歌
            result = []
            for i, para in enumerate(lines):
                if i == 0:
                    result.append(f"【主歌】\n{para}")
                elif i == 1:
                    result.append(f"【副歌】\n{para}")
                elif i == 2:
                    result.append(f"【主歌二】\n{para}")
                elif i == 3:
                    result.append(f"【副歌】\n{para}")
                else:
                    result.append(para)
            return '\n\n'.join(result)
        
        return text


class LyricsGenerator:
    """歌词生成器"""
    
    def __init__(self):
        self._models: Dict[int, MarkovModel] = {}
        self.post_processor = LyricsPostProcessor()
    
    def load_model(self, model_id: int) -> Optional[MarkovModel]:
        """加载模型"""
        if model_id in self._models:
            return self._models[model_id]
        
        model = training_service.load_model(model_id)
        if model:
            self._models[model_id] = model
        return model
    
    def generate_continue(
        self,
        model_id: int,
        prompt: str,
        config: GenerationConfig
    ) -> str:
        """
        续写模式
        
        基于输入文本继续生成歌词
        """
        model = self.load_model(model_id)
        if not model:
            raise ValueError(f"模型 {model_id} 不存在或未加载")
        
        # 使用模型生成
        generated = model.generate(
            max_length=config.max_length,
            temperature=config.temperature
        )
        
        # 如果有提示词，拼接
        if prompt:
            generated = prompt + generated
        
        # 后处理
        result = self.post_processor.remove_repetition(generated)
        result = self.post_processor.format_lyrics(result)
        
        return result
    
    def generate_topic(
        self,
        model_id: int,
        topic: str,
        config: GenerationConfig
    ) -> str:
        """
        主题模式
        
        基于主题词生成歌词
        """
        model = self.load_model(model_id)
        if not model:
            raise ValueError(f"模型 {model_id} 不存在或未加载")
        
        # 从主题词开始生成
        generated = model.generate(
            max_length=config.max_length,
            temperature=config.temperature
        )
        
        # 后处理
        result = self.post_processor.remove_repetition(generated)
        result = self.post_processor.format_lyrics(result)
        
        # 添加主题标记
        if topic:
            result = f"【{topic}】\n{result}"
        
        return result
    
    def generate_random(
        self,
        model_id: int,
        config: GenerationConfig
    ) -> str:
        """
        随机模式
        
        随机生成歌词
        """
        model = self.load_model(model_id)
        if not model:
            raise ValueError(f"模型 {model_id} 不存在或未加载")
        
        # 随机生成
        generated = model.generate(
            max_length=config.max_length,
            temperature=config.temperature
        )
        
        # 后处理
        result = self.post_processor.remove_repetition(generated)
        result = self.post_processor.format_lyrics(result)
        result = self.post_processor.add_structure(result)
        
        return result
    
    def generate_with_style_fusion(
        self,
        model_ids: List[int],
        weights: List[float],
        config: GenerationConfig
    ) -> str:
        """
        风格融合模式
        
        混合多个模型的风格
        """
        # MVP: 简单地轮流生成
        # 生产环境可以实现更复杂的融合算法
        
        if not model_ids:
            raise ValueError("至少需要一个模型")
        
        results = []
        for model_id in model_ids:
            try:
                text = self.generate_random(model_id, config)
                results.append(text)
            except Exception as e:
                logger.warning(f"模型 {model_id} 生成失败: {e}")
        
        if not results:
            raise ValueError("所有模型生成失败")
        
        # 简单拼接（可以改进为更智能的融合）
        final_result = results[0]
        
        return final_result


class GenerationService:
    """生成服务 - 对外接口"""
    
    def __init__(self):
        self.generator = LyricsGenerator()
        self._generation_history: Dict[int, List[GenerationResult]] = {}
    
    async def generate(
        self,
        model_id: int,
        mode: str = "random",
        prompt: Optional[str] = None,
        topic: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        生成歌词
        
        Args:
            model_id: 模型ID
            mode: 生成模式 (continue, topic, random)
            prompt: 提示文本（续写模式）
            topic: 主题词（主题模式）
            config: 生成配置
        
        Returns:
            生成结果
        """
        if config is None:
            config = GenerationConfig()
        
        # 检查模型是否存在
        if not training_service.model_exists(model_id):
            # 使用默认模板生成（MVP fallback）
            return await self._generate_with_template(model_id, mode, prompt, topic, config)
        
        # 使用训练好的模型生成
        try:
            if mode == "continue":
                text = self.generator.generate_continue(model_id, prompt or "", config)
            elif mode == "topic":
                text = self.generator.generate_topic(model_id, topic or "主题", config)
            else:  # random
                text = self.generator.generate_random(model_id, config)
            
            result = GenerationResult(
                text=text,
                mode=mode,
                config=config,
                model_id=model_id
            )
            
            # 记录历史
            if model_id not in self._generation_history:
                self._generation_history[model_id] = []
            self._generation_history[model_id].append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"生成失败: {e}")
            # fallback 到模板生成
            return await self._generate_with_template(model_id, mode, prompt, topic, config)
    
    async def _generate_with_template(
        self,
        model_id: int,
        mode: str,
        prompt: Optional[str],
        topic: Optional[str],
        config: GenerationConfig
    ) -> GenerationResult:
        """
        使用模板生成歌词（MVP fallback）
        
        当模型不存在时使用预定义的歌词模板
        """
        # 预定义的歌词模板
        templates = {
            "continue": [
                "{prompt}\n风吹过脸庞\n带走昨日的忧伤\n心中依然有光\n照亮前行的方向\n\n时光匆匆流淌\n记忆静静沉淀\n那些未说的话语\n都化作漫天星光",
                "{prompt}\n月光洒在窗前\n思念悄悄蔓延\n远方的你是否入眠\n梦中可有我的容颜\n\n夜深人静时\n心事无处安放\n愿风儿轻轻吹\n带去我的念想",
                "{prompt}\n花开花落年复年\n潮起潮落月复月\n生命中有太多遇见\n而你是最美的那个\n\n岁月无声\n时光有情\n珍惜当下\n不负流年"
            ],
            "topic": [
                "【{topic}】\n风吹过山岗\n云飘向远方\n心中有一首歌\n唱不尽的思念\n\n{topic}在心间\n化作永恒的诗篇\n无论时光如何变迁\n这份情永远不变",
                "【{topic}】\n清晨第一缕阳光\n照亮了我的脸庞\n想起你温柔的模样\n心中充满希望\n\n{topic}如诗如画\n镌刻在时光里\n那些美好的瞬间\n永远不会忘记",
                "【{topic}】\n夜空中最亮的星\n指引着前行方向\n穿越黑暗的力量\n来自心中的梦想\n\n{topic}是力量\n让我们勇敢飞翔\n不怕风雨阻挡\n终会到达远方"
            ],
            "random": [
                "【主歌】\n春风轻拂绿柳梢\n桃花依旧笑春风\n往事如烟散如雾\n此情此景忆旧容\n\n【副歌】\n人生若只如初见\n何事秋风悲画扇\n等闲变却故人心\n却道故人心易变\n\n【主歌二】\n青山不改水长流\n岁月无声人依旧\n且把酒杯举过头\n畅饮人间万古愁",
                "【主歌】\n月光如水洒满地\n照亮心中那片天\n繁星点点闪光芒\n陪我度过这长夜\n\n【副歌】\n愿时光温柔以待\n愿岁月不负韶华\n愿你我心中有爱\n愿梦想都能开花\n\n【主歌二】\n风雨过后见彩虹\n努力终会有回报\n珍惜每一个今天\n拥抱每一个明天",
                "【主歌】\n细雨蒙蒙润心田\n微风徐徐送清凉\n人生处处有风景\n何必苦苦寻远方\n\n【副歌】\n珍惜眼前的美好\n感恩生命中的遇见\n用心感受每一天\n平凡中也有惊艳\n\n【主歌二】\n春天播种希望\n夏天收获成长\n秋天品味丰收\n冬天积蓄力量"
            ]
        }
        
        # 选择模板
        mode_templates = templates.get(mode, templates["random"])
        template = random.choice(mode_templates)
        
        # 填充模板
        if mode == "continue":
            text = template.format(prompt=prompt or "往事如风")
        elif mode == "topic":
            text = template.format(topic=topic or "梦想")
        else:
            text = template
        
        # 模拟生成延迟
        await asyncio.sleep(0.5 + random.random() * 0.5)
        
        result = GenerationResult(
            text=text,
            mode=mode,
            config=config,
            model_id=model_id
        )
        
        return result
    
    def get_history(self, model_id: int, limit: int = 20) -> List[GenerationResult]:
        """获取生成历史"""
        return self._generation_history.get(model_id, [])[-limit:]
    
    def clear_history(self, model_id: int):
        """清空生成历史"""
        if model_id in self._generation_history:
            del self._generation_history[model_id]
    
    def generate_variations(
        self,
        model_id: int,
        base_text: str,
        count: int = 3,
        config: Optional[GenerationConfig] = None
    ) -> List[str]:
        """
        生成变体
        
        基于已有歌词生成多个变体版本
        """
        if config is None:
            config = GenerationConfig()
        
        variations = []
        
        for i in range(count):
            # 调整温度增加多样性
            varied_config = GenerationConfig(
                temperature=config.temperature + i * 0.1,
                max_length=config.max_length,
                top_p=config.top_p,
                top_k=config.top_k,
                repetition_penalty=config.repetition_penalty
            )
            
            try:
                result = self.generate_continue(model_id, base_text, varied_config)
                variations.append(result)
            except Exception as e:
                logger.warning(f"生成变体 {i} 失败: {e}")
        
        return variations


# 单例服务
generation_service = GenerationService()
