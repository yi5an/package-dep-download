#!/bin/bash

# Docker Compose 测试脚本

set -e

echo "========================================="
echo "  Docker Compose 部署测试"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker
echo "1. 检查 Docker 安装..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 已安装: $(docker --version)${NC}"

# 检查 Docker Compose
echo ""
echo "2. 检查 Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose 已安装${NC}"

# 停止现有容器
echo ""
echo "3. 停止现有容器..."
docker-compose down 2>/dev/null || true
echo -e "${GREEN}✓ 已停止现有容器${NC}"

# 构建镜像
echo ""
echo "4. 构建 Docker 镜像..."
docker-compose build
echo -e "${GREEN}✓ 镜像构建成功${NC}"

# 启动服务
echo ""
echo "5. 启动服务..."
docker-compose up -d
echo -e "${GREEN}✓ 服务已启动${NC}"

# 等待服务就绪
echo ""
echo "6. 等待服务就绪..."
sleep 5

# 检查容器状态
echo ""
echo "7. 检查容器状态..."
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ 容器运行中${NC}"
    docker-compose ps
else
    echo -e "${RED}✗ 容器启动失败${NC}"
    docker-compose logs
    exit 1
fi

# 健康检查
echo ""
echo "8. 执行健康检查..."
HEALTH_CHECK_URL="http://localhost:8000/api/health"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
        echo ""
        curl -s "$HEALTH_CHECK_URL" | python3 -m json.tool
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}等待服务就绪... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ 健康检查失败${NC}"
    echo ""
    echo "查看日志:"
    docker-compose logs --tail=50
    exit 1
fi

# 功能测试
echo ""
echo "9. 执行功能测试..."
echo "   测试下载 vim-enhanced 包..."
TASK_ID=$(curl -s -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "packages": ["vim-enhanced"],
    "system_type": "rpm",
    "distribution": "centos-7",
    "arch": "x86_64",
    "deep_download": false
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

echo "   任务 ID: $TASK_ID"

if [ -n "$TASK_ID" ]; then
    echo -e "${GREEN}✓ API 测试通过${NC}"
else
    echo -e "${RED}✗ API 测试失败${NC}"
    exit 1
fi

# 显示日志
echo ""
echo "10. 显示服务日志..."
docker-compose logs --tail=20

# 显示访问信息
echo ""
echo "========================================="
echo -e "${GREEN}  ✓ Docker Compose 部署成功！${NC}"
echo "========================================="
echo ""
echo "服务访问地址:"
echo "  - Web UI: http://localhost:8000"
echo "  - API Health: http://localhost:8000/api/health"
echo ""
echo "常用命令:"
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "  - 进入容器: docker-compose exec web bash"
echo ""
echo "数据持久化:"
echo "  - 下载目录: ./downloads"
echo "  - 日志目录: ./logs"
echo ""

# 保持容器运行
read -p "按 Enter 键停止服务并退出..."
docker-compose down

echo ""
echo -e "${GREEN}已停止服务${NC}"
