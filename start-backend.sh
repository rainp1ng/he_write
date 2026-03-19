#!/bin/bash

# he_write 后端启动脚本
# 用于本地开发环境

set -e

echo "==================================="
echo "he_write 后端启动"
echo "==================================="

# 进入后端目录
cd "$(dirname "$0")/backend"

# 检查 Python 版本
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "错误: 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

echo "使用 Python: $($PYTHON --version)"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    $PYTHON -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 创建必要目录
mkdir -p data models

# 启动服务
echo "启动后端服务..."
echo "API 文档: http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
