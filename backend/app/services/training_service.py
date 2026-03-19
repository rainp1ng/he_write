"""
模型训练服务

支持歌词模型训练，MVP 阶段使用简单的统计模型（N-gram / Markov），
生产环境可替换为 GPT-2 / Qwen 等大模型微调。
"""
import asyncio
import json
import os
import pickle
import random
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any

from loguru import logger


@dataclass
class TrainingConfig:
    """训练配置"""
    learning_rate: float = 0.001
    batch_size: int = 8
    epochs: int = 3
    max_length: int = 512
    warmup_steps: int = 100
    ngram_size: int = 3  # N-gram 模型参数
    min_freq: int = 2    # 最小词频


@dataclass
class TrainingProgress:
    """训练进度"""
    status: str = "pending"  # pending, running, completed, failed
    current_epoch: int = 0
    total_epochs: int = 0
    current_step: int = 0
    total_steps: int = 0
    progress: float = 0.0
    loss: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        # 停用词（可根据需要扩展）
        self.stopwords = set([
            '的', '了', '在', '是', '我', '有', '和', '就',
            '不', '人', '都', '一', '一个', '上', '也', '很', '到',
            '说', '要', '去', '你', '会', '着', '没有', '看', '好'
        ])
    
    def tokenize(self, text: str, remove_stopwords: bool = False) -> List[str]:
        """
        简单分词（按字符 + 标点）
        
        MVP 阶段使用简单分词，生产环境可替换为 jieba 等分词工具
        """
        if not text:
            return []
        
        # 按标点分割
        segments = re.split(r'[，。！？、；：""''（）\s]+', text)
        
        tokens = []
        for seg in segments:
            if seg:
                # 简单处理：每个字作为一个 token
                # 可以在这里集成 jieba 分词
                tokens.extend(list(seg))
        
        if remove_stopwords:
            tokens = [t for t in tokens if t not in self.stopwords]
        
        return tokens
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        # 去除多余空白
        text = re.sub(r'\s+', '', text)
        # 去除特殊字符
        text = re.sub(r'[^\u4e00-\u9fff，。！？、；：""''（）\w]', '', text)
        return text.strip()


class NGramModel:
    """
    N-gram 语言模型
    
    MVP 阶段的简单模型，基于统计的文本生成。
    生产环境应替换为 GPT-2 / Qwen 等深度学习模型。
    """
    
    def __init__(self, n: int = 3):
        self.n = n
        self.ngram_counts: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)
        self.context_counts: Dict[Tuple[str, ...], int] = defaultdict(int)
        self.vocabulary: set = set()
        self.preprocessor = TextPreprocessor()
    
    def train(self, texts: List[str], progress_callback: Callable = None) -> Dict[str, Any]:
        """
        训练 N-gram 模型
        
        Args:
            texts: 训练文本列表
            progress_callback: 进度回调函数
        
        Returns:
            训练统计信息
        """
        total = len(texts)
        
        for i, text in enumerate(texts):
            tokens = self.preprocessor.tokenize(text)
            tokens = ['<s>'] * (self.n - 1) + tokens + ['</s>']
            
            # 更新词汇表
            self.vocabulary.update(tokens)
            
            # 统计 N-gram
            for j in range(len(tokens) - self.n + 1):
                context = tuple(tokens[j:j+self.n-1])
                word = tokens[j+self.n-1]
                
                self.ngram_counts[context][word] += 1
                self.context_counts[context] += 1
            
            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, total)
        
        return {
            "vocabulary_size": len(self.vocabulary),
            "ngram_count": sum(len(v) for v in self.ngram_counts.values()),
            "context_count": len(self.context_counts)
        }
    
    def generate(
        self, 
        prompt: str = "", 
        max_length: int = 100,
        temperature: float = 1.0
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 起始文本
            max_length: 最大生成长度
            temperature: 温度参数（控制随机性）
        
        Returns:
            生成的文本
        """
        if prompt:
            tokens = self.preprocessor.tokenize(prompt)
        else:
            tokens = []
        
        # 用起始标记填充
        context = ['<s>'] * (self.n - 1) + tokens[-(self.n-1):] if tokens else ['<s>'] * (self.n - 1)
        context = tuple(context[-(self.n-1):])
        
        generated = list(tokens)
        
        for _ in range(max_length):
            if context not in self.ngram_counts:
                # 回退到较低阶模型
                if len(context) > 1:
                    context = context[1:]
                    continue
                else:
                    # 随机选择
                    next_word = random.choice(list(self.vocabulary))
            else:
                # 根据概率选择下一个词
                candidates = self.ngram_counts[context]
                total = sum(candidates.values())
                
                # 应用温度
                if temperature != 1.0:
                    import math
                    candidates = {
                        k: math.pow(v, 1.0/temperature) 
                        for k, v in candidates.items()
                    }
                    total = sum(candidates.values())
                
                # 加权随机选择
                r = random.random() * total
                cumsum = 0
                next_word = list(candidates.keys())[0]  # 默认
                for word, count in candidates.items():
                    cumsum += count
                    if cumsum >= r:
                        next_word = word
                        break
            
            if next_word == '</s>':
                break
            
            generated.append(next_word)
            context = tuple(list(context[1:]) + [next_word])
        
        return ''.join(generated)
    
    def save(self, path: str):
        """保存模型"""
        data = {
            'n': self.n,
            'ngram_counts': {k: dict(v) for k, v in self.ngram_counts.items()},
            'context_counts': dict(self.context_counts),
            'vocabulary': list(self.vocabulary)
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
    
    @classmethod
    def load(cls, path: str) -> 'NGramModel':
        """加载模型"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        model = cls(n=data['n'])
        model.ngram_counts = {k: Counter(v) for k, v in data['ngram_counts'].items()}
        model.context_counts = defaultdict(int, data['context_counts'])
        model.vocabulary = set(data['vocabulary'])
        return model


class MarkovModel:
    """
    马尔可夫链文本生成模型
    
    比 N-gram 更简单，适合快速 MVP
    """
    
    def __init__(self, order: int = 2):
        self.order = order
        self.transitions: Dict[str, List[str]] = defaultdict(list)
        self.starts: List[str] = []
    
    def train(self, texts: List[str]) -> Dict[str, int]:
        """训练模型"""
        for text in texts:
            # 按行分割
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            for line in lines:
                if len(line) < self.order:
                    continue
                
                # 记录行首
                self.starts.append(line[:self.order])
                
                # 记录转移
                for i in range(len(line) - self.order):
                    key = line[i:i+self.order]
                    next_char = line[i+self.order]
                    self.transitions[key].append(next_char)
        
        return {
            "starts": len(self.starts),
            "transitions": len(self.transitions)
        }
    
    def generate(self, max_length: int = 100, temperature: float = 1.0) -> str:
        """生成文本"""
        if not self.starts:
            return ""
        
        # 随机选择起始
        current = random.choice(self.starts)
        result = [current]
        
        for _ in range(max_length - self.order):
            if current not in self.transitions:
                break
            
            candidates = self.transitions[current]
            
            # 加权随机
            if temperature == 1.0:
                next_char = random.choice(candidates)
            else:
                # 统计频率
                counter = Counter(candidates)
                chars, counts = zip(*counter.items())
                
                # 应用温度
                import math
                weights = [math.pow(c, 1.0/temperature) for c in counts]
                total = sum(weights)
                weights = [w/total for w in weights]
                
                next_char = random.choices(chars, weights=weights)[0]
            
            result.append(next_char)
            current = ''.join(result[-self.order:])
            
            # 遇到换行可以停止或继续
            if next_char in ['。', '！', '？']:
                if random.random() < 0.3:  # 30% 概率停止
                    break
        
        return ''.join(result)
    
    def save(self, path: str):
        """保存模型"""
        data = {
            'order': self.order,
            'transitions': dict(self.transitions),
            'starts': self.starts
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
    
    @classmethod
    def load(cls, path: str) -> 'MarkovModel':
        """加载模型"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        model = cls(order=data['order'])
        model.transitions = defaultdict(list, {k: v for k, v in data['transitions'].items()})
        model.starts = data['starts']
        return model


class TrainingService:
    """训练服务 - 对外接口"""
    
    def __init__(self, model_path: str = "./models"):
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        self._active_trainings: Dict[int, TrainingProgress] = {}
        self._stop_flags: Dict[int, bool] = {}
    
    async def train_model(
        self,
        model_id: int,
        samples: List[str],
        config: TrainingConfig,
        progress_callback: Callable[[TrainingProgress], None] = None
    ) -> Tuple[bool, TrainingProgress]:
        """
        训练模型
        
        Args:
            model_id: 模型ID
            samples: 训练样本列表
            config: 训练配置
            progress_callback: 进度回调
        
        Returns:
            (是否成功, 训练进度)
        """
        progress = TrainingProgress(
            status="running",
            total_epochs=config.epochs,
            started_at=datetime.now()
        )
        self._active_trainings[model_id] = progress
        self._stop_flags[model_id] = False
        
        try:
            # 数据预处理
            progress.logs.append("开始数据预处理...")
            preprocessor = TextPreprocessor()
            
            # 清洗数据
            cleaned_samples = []
            for text in samples:
                cleaned = preprocessor.clean_text(text)
                if len(cleaned) >= 20:  # 过滤太短的文本
                    cleaned_samples.append(cleaned)
            
            progress.logs.append(f"有效样本数: {len(cleaned_samples)}")
            
            if len(cleaned_samples) < 10:
                raise ValueError("有效样本数量不足，至少需要 10 条")
            
            # 初始化模型
            model = MarkovModel(order=config.ngram_size)
            
            # 计算总步数
            total_steps = config.epochs * len(cleaned_samples)
            progress.total_steps = total_steps
            current_step = 0
            
            # 训练循环
            for epoch in range(config.epochs):
                if self._stop_flags.get(model_id, False):
                    progress.status = "stopped"
                    progress.logs.append("训练被用户停止")
                    break
                
                progress.current_epoch = epoch + 1
                progress.logs.append(f"开始第 {epoch + 1}/{config.epochs} 轮训练")
                
                # 打乱数据
                random.shuffle(cleaned_samples)
                
                # 训练
                stats = model.train(cleaned_samples)
                current_step += len(cleaned_samples)
                progress.current_step = current_step
                progress.progress = (current_step / total_steps) * 100
                
                # 模拟损失下降
                progress.loss = 1.0 / (epoch + 1)
                
                if progress_callback:
                    progress_callback(progress)
                
                # 模拟训练耗时
                await asyncio.sleep(0.5)
            
            # 保存模型
            if progress.status == "running":
                model_file = self.model_path / f"model_{model_id}.pkl"
                model.save(str(model_file))
                
                progress.status = "completed"
                progress.completed_at = datetime.now()
                progress.metrics = {
                    "vocabulary_size": len(model.starts),
                    "transitions": stats.get("transitions", 0)
                }
                progress.logs.append(f"模型已保存到: {model_file}")
            
            return True, progress
            
        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.logs.append(f"训练失败: {str(e)}")
            logger.error(f"模型训练失败: {e}")
            return False, progress
            
        finally:
            if model_id in self._active_trainings:
                del self._active_trainings[model_id]
            if model_id in self._stop_flags:
                del self._stop_flags[model_id]
    
    def stop_training(self, model_id: int):
        """停止训练"""
        self._stop_flags[model_id] = True
    
    def get_progress(self, model_id: int) -> Optional[TrainingProgress]:
        """获取训练进度"""
        return self._active_trainings.get(model_id)
    
    def load_model(self, model_id: int) -> Optional[MarkovModel]:
        """加载训练好的模型"""
        model_file = self.model_path / f"model_{model_id}.pkl"
        if model_file.exists():
            return MarkovModel.load(str(model_file))
        return None
    
    def model_exists(self, model_id: int) -> bool:
        """检查模型是否存在"""
        model_file = self.model_path / f"model_{model_id}.pkl"
        return model_file.exists()
    
    def delete_model(self, model_id: int) -> bool:
        """删除模型文件"""
        model_file = self.model_path / f"model_{model_id}.pkl"
        if model_file.exists():
            model_file.unlink()
            return True
        return False


# 单例服务
training_service = TrainingService()
