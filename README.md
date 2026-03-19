# he_write - 作词人训练系统

一个基于 AI 的作词人风格训练与歌词生成系统。通过采集作词人的歌词作品，训练特定风格的生成模型，创作出相似风格的歌词。

## 功能特性

- **作词人信息采集**：输入作词人姓名，自动从网易云、QQ音乐等平台爬取歌词
- **样本库管理**：手动管理歌词样本，支持分类、标签、质量评分
- **模型训练**：基于歌词样本训练特定风格的作词人模型
- **歌词生成**：输入关键词/主题，生成特定作词人风格的歌词

## 技术栈

### 前端
- Next.js 14 - React 框架
- TypeScript - 类型安全
- TailwindCSS - 样式框架
- shadcn/ui - UI 组件库
- Zustand - 状态管理

### 后端
- Python 3.10+
- FastAPI - 高性能异步框架
- SQLAlchemy - ORM
- SQLite/PostgreSQL - 数据库

### AI 模型
- MVP 阶段：N-Gram / Markov 统计模型
- 生产环境：GPT-2 Chinese / Qwen

## 项目结构

```
he_write/
├── frontend/                 # Next.js 前端
│   ├── src/
│   │   ├── app/             # App Router 页面
│   │   ├── components/      # React 组件
│   │   └── lib/             # 工具库
│   └── package.json
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务逻辑
│   │   │   ├── crawler_service.py   # 爬虫服务
│   │   │   ├── training_service.py  # 训练服务
│   │   │   └── generation_service.py # 生成服务
│   │   └── core/            # 核心配置
│   ├── requirements.txt
│   └── main.py
└── docs/                     # 文档
    ├── DESIGN.md            # 设计文档
    └── DEVELOPMENT.md       # 开发文档
```

## 快速开始

### 环境要求

- Node.js >= 18.0.0
- Python >= 3.10
- pip / pnpm
- Docker & Docker Compose (可选)

### 方式一：Docker 启动 (推荐)

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：本地启动

#### 后端启动

```bash
# 使用启动脚本
./start-backend.sh

# 或手动启动
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
python test_backend.py

# 启动服务
python main.py
# 或
uvicorn main:app --reload --port 8000
```

#### 前端启动

```bash
# 使用启动脚本
./start-frontend.sh

# 或手动启动
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## API 接口

### 作词人管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/lyricists | 获取作词人列表 |
| POST | /api/lyricists | 创建作词人 |
| GET | /api/lyricists/{id} | 获取作词人详情 |
| POST | /api/lyricists/{id}/crawl | 开始采集歌词 |

### 样本管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/samples | 获取样本列表 |
| POST | /api/samples | 创建样本 |
| POST | /api/samples/import | 批量导入样本 |

### 模型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/models | 获取模型列表 |
| POST | /api/models | 创建训练任务 |
| GET | /api/models/{id}/status | 获取训练状态 |

### 歌词生成

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/generation/generate | 生成歌词 |
| GET | /api/generation/history | 生成历史 |

## 使用流程

1. **创建作词人**：在「作词人」页面添加作词人信息
2. **采集歌词**：点击「开始采集」自动爬取歌词
3. **管理样本**：在「样本库」审核和管理歌词样本
4. **训练模型**：选择样本，开始训练作词人模型
5. **生成歌词**：在「生成」页面输入主题，创作歌词

## 注意事项

⚠️ **免责声明**

- 本系统仅供学习研究使用
- 爬取的歌词版权归原作者所有
- 生成的歌词仅供创意参考，不用于商业用途

## 许可证

MIT License
