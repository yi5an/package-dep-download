#!/bin/bash

# Docker 部署测试脚本
# 用于测试 Docker 构建和部署

set -e

echo "=== Docker 部署测试 ==="
echo

# 检查 Docker 是否运行
echo "1. 检查 Docker 服务..."
if ! docker info &> /dev/null; then
    echo "错误: Docker 服务未运行"
    exit 1
fi
echo "✓ Docker 服务正常"
echo

# 构建镜像
echo "2. 构建 Docker 镜像..."
if docker-compose build; then
    echo "✓ 镜像构建成功"
else
    echo "✗ 镜像构建失败"
    exit 1
fi
echo

# 启动服务
echo "3. 启动 Docker 服务..."
if docker-compose up -d; then
    echo "✓ 服务启动成功"
else
    echo "✗ 服务启动失败"
    exit 1
fi
echo

# 等待服务就绪
echo "4. 等待服务就绪..."
sleep 5
echo

# 健康检查
echo "5. 执行健康检查..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/api/health &> /dev/null; then
        echo "✓ 健康检查通过"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "等待服务就绪... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "✗ 健康检查失败"
    docker-compose logs --tail=50
    exit 1
fi
echo

# 显示容器状态
echo "6. 容器状态:"
docker-compose ps
echo

# 显示最近日志
echo "7. 最近日志:"
docker-compose logs --tail=20
echo

# 提示信息
echo "=== 测试完成 ==="
echo
echo "服务已启动并运行在 http://localhost:8000"
echo
echo "停止服务: docker-compose down"
echo "查看日志: docker-compose logs -f"
echo "重启服务: docker-compose restart"
echo
