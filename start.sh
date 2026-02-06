#!/bin/bash
# FastAPI 应用启动脚本

echo "🚀 启动离线软件包下载服务..."

# 激活虚拟环境
source venv/bin/activate

# 启动应用
python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
