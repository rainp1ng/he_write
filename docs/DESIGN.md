# he_write 作词人训练系统 - 设计文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  作词人   │ │  样本库   │ │  模型训练  │ │  歌词生成  │       │
│  │  采集     │ │  管理     │ │  监控     │ │  编辑     │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API / WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  Crawler  │ │  Sample   │ │  Training  │ │ Generation│       │
│  │  Service  │ │  Service  │ │  Service  │ │  Service  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Data & Model Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  PostgreSQL │  │  Redis      │  │  Model      │             │
│  │  (SQLite)   │  │  (Cache)    │  │  Storage    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 技术栈详细选择

### 2.1 前端技术栈
| 技术 | 版本 | 选择理由 |
|------|------|----------|
| Next.js | 14.x | SSR/SSG 支持，SEO 友好，路由内置 |
| React | 18.x | 组件化开发，生态成熟 |
| TypeScript | 5.x | 类型安全，开发体验好 |
| Tailwind CSS | 3.x | 快速样式开发 |
| shadcn/ui | latest | 高质量组件库 |
| Zustand | 4.x | 轻量状态管理 |
| React Query | 5.x | 数据请求缓存 |
| Monaco Editor | latest | 代码/文本编辑器 |

### 2.2 后端技术栈
| 技术 | 版本 | 选择理由 |
|------|------|----------|
| Python | 3.10+ | AI/ML 生态丰富 |
| FastAPI | 0.109+ | 高性能异步框架，自动 API 文档 |
| SQLAlchemy | 2.x | ORM 支持 |
| Pydantic | 2.x | 数据验证 |
| Celery | 5.x | 异步任务队列（训练任务） |
| Redis | 7.x | 缓存、任务队列 |

### 2.3 AI 模型选型分析

#### 方案对比
| 模型 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| GPT-2 Chinese | 训练快、资源低、中文支持好 | 生成质量一般 | MVP 快速验证 |
| Qwen-1.8B | 中文能力强、生成质量高 | 资源需求稍高 | 生产环境推荐 |
| LSTM | 轻量、快速 | 长文本效果差 | 简单场景 |

#### 最终选择
- **MVP 阶段**: GPT-2 Chinese (uer/gpt2-chinese-cluecorpussmall)
  - 参数量: 124M/345M
  - 显存需求: 4-8GB
  - 训练时间: 1-4小时 (1000样本)
  - 部署简单，推理快速

- **生产阶段**: Qwen-1.8B
  - 中文理解能力强
  - 可 fine-tune

### 2.4 数据库设计

#### 主要表结构

```sql
-- 作词人表
CREATE TABLE lyricists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    alias VARCHAR(200),  -- 别名
    style VARCHAR(50),   -- 风格标签
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 歌词样本表
CREATE TABLE lyrics_samples (
    id SERIAL PRIMARY KEY,
    lyricist_id INTEGER REFERENCES lyricists(id),
    title VARCHAR(200),
    content TEXT NOT NULL,
    source VARCHAR(100),  -- 来源
    source_url VARCHAR(500),
    year INTEGER,
    tags VARCHAR(200),    -- JSON 数组
    quality_score FLOAT,  -- 质量评分
    status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 模型表
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    lyricist_id INTEGER REFERENCES lyricists(id),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20),
    base_model VARCHAR(100),  -- 基础模型
    model_path VARCHAR(500),  -- 模型文件路径
    config JSON,              -- 训练配置
    metrics JSON,             -- 训练指标
    status VARCHAR(20) DEFAULT 'pending',  -- pending/training/completed/failed
    created_at TIMESTAMP DEFAULT NOW(),
    trained_at TIMESTAMP
);

-- 生成记录表
CREATE TABLE generations (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    input_text TEXT,
    parameters JSON,  -- 生成参数
    output_text TEXT,
    rating INTEGER,   -- 用户评分
    is_saved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 训练任务表
CREATE TABLE training_tasks (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    status VARCHAR(20),  -- pending/running/completed/failed
    progress FLOAT,      -- 0-100
    current_step INTEGER,
    total_steps INTEGER,
    logs TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

## 3. 功能模块设计

### 3.1 作词人信息采集模块

```
采集流程:
1. 用户输入作词人姓名
2. 多源搜索 (网易云音乐、QQ音乐、歌词网站)
3. 数据抓取 + 反爬处理
4. 数据清洗 (去重、格式化、分割)
5. 人工审核 + 质量评估
```

**支持的爬虫源**:
- 网易云音乐 (music.163.com)
- QQ音乐 (y.qq.com)
- 酷狗音乐
- 歌词网站 (gecimi.com 等)

**反爬策略**:
- 请求间隔随机化
- User-Agent 轮换
- 代理池支持
- 登录态管理

### 3.2 样本库管理模块

**功能**:
- 手动增删改查
- 批量导入 (CSV/JSON/TXT)
- 分类标签管理
- 质量评分 (自动 + 手动)
- 去重检测
- 预览和搜索

### 3.3 模型训练模块

**训练流程**:
1. 数据预处理 (分词、清洗)
2. 数据集划分 (训练/验证/测试)
3. 模型配置 (学习率、批次等)
4. 启动训练 (后台任务)
5. 实时监控进度
6. 评估模型质量
7. 版本管理

**训练参数**:
- learning_rate: 1e-5 ~ 5e-5
- batch_size: 4-16
- epochs: 3-10
- max_length: 512
- warmup_steps: 100

### 3.4 歌词生成模块

**生成模式**:
1. **续写模式**: 给定开头，续写歌词
2. **主题模式**: 给定主题词，生成完整歌词
3. **随机模式**: 随机生成
4. **风格融合**: 多个作词人风格混合

**生成参数**:
- temperature: 0.7-1.2 (创意度)
- top_p: 0.8-0.95
- top_k: 40-100
- max_length: 200-500
- repetition_penalty: 1.0-1.5

## 4. API 设计

### 4.1 作词人 API
```
GET    /api/lyricists           # 列表
POST   /api/lyricists           # 创建
GET    /api/lyricists/{id}      # 详情
PUT    /api/lyricists/{id}      # 更新
DELETE /api/lyricists/{id}      # 删除
POST   /api/lyricists/{id}/crawl # 开始采集
GET    /api/lyricists/{id}/crawl/status # 采集状态
```

### 4.2 样本 API
```
GET    /api/samples             # 列表
POST   /api/samples             # 创建
GET    /api/samples/{id}        # 详情
PUT    /api/samples/{id}        # 更新
DELETE /api/samples/{id}        # 删除
POST   /api/samples/import      # 批量导入
POST   /api/samples/deduplicate # 去重检测
```

### 4.3 模型 API
```
GET    /api/models              # 列表
POST   /api/models              # 创建训练任务
GET    /api/models/{id}         # 详情
DELETE /api/models/{id}         # 删除
GET    /api/models/{id}/status  # 训练状态
POST   /api/models/{id}/stop    # 停止训练
```

### 4.4 生成 API
```
POST   /api/generate            # 生成歌词
GET    /api/generations         # 生成历史
POST   /api/generations/{id}/save # 保存结果
POST   /api/generations/{id}/rate # 评分
```

## 5. 目录结构

```
he_write/
├── frontend/                    # Next.js 前端
│   ├── src/
│   │   ├── app/                 # App Router
│   │   ├── components/          # 组件
│   │   │   ├── ui/              # 基础 UI 组件
│   │   │   ├── lyricist/        # 作词人相关组件
│   │   │   ├── sample/          # 样本相关组件
│   │   │   ├── model/           # 模型相关组件
│   │   │   └── generate/        # 生成相关组件
│   │   ├── lib/                 # 工具库
│   │   ├── hooks/               # React Hooks
│   │   ├── stores/              # 状态管理
│   │   └── types/               # TypeScript 类型
│   ├── public/
│   ├── package.json
│   └── next.config.js
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   ├── models/              # 数据模型
│   │   ├── schemas/             # Pydantic Schema
│   │   ├── services/            # 业务逻辑
│   │   │   ├── crawler/         # 爬虫服务
│   │   │   ├── sample/          # 样本服务
│   │   │   ├── training/        # 训练服务
│   │   │   └── generation/      # 生成服务
│   │   ├── core/                # 核心配置
│   │   └── utils/               # 工具函数
│   ├── requirements.txt
│   └── main.py
│
├── models/                      # 模型存储目录
├── data/                        # 数据存储目录
├── docs/                        # 文档
│   ├── DESIGN.md
│   └── DEVELOPMENT.md
└── README.md
```

## 6. 安全考虑

1. **API 认证**: JWT Token 认证
2. **输入验证**: Pydantic 严格校验
3. **SQL 注入**: SQLAlchemy 参数化查询
4. **XSS 防护**: 前端输出转义
5. **爬虫合规**: 
   - 遵守 robots.txt
   - 添加请求间隔
   - 标识爬虫身份
