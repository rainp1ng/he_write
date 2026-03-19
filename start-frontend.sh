#!/bin/bash

# he_write 前端启动脚本
# 用于本地开发环境

set -e

echo "==================================="
echo "he_write 前端启动"
echo "==================================="

# 进入前端目录
cd "$(dirname "$0")/frontend"

# 检查 Node 版本
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

echo "使用 Node: $(node --version)"

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install
fi

# 启动开发服务器
echo "启动前端开发服务器..."
echo "访问地址: http://localhost:3000"
echo ""

npm run dev
