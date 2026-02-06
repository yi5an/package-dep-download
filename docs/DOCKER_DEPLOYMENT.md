# Docker 部署指南

本文档介绍如何使用 Docker 部署包依赖下载工具。

## 前置要求

- Docker (>= 20.10)
- Docker Compose (>= 2.0)

## 快速开始

### 1. 构建镜像

```bash
docker-compose build
```

### 2. 启动服务

```bash
docker-compose up -d
```

服务将在 `http://localhost:8000` 启动。

### 3. 检查服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 健康检查
curl http://localhost:8000/api/health
```

### 4. 停止服务

```bash
docker-compose down
```

## 配置

环境变量可以在 `docker-compose.yml` 中配置：

```yaml
environment:
  - MAX_CONCURRENT_DOWNLOADS=3    # 最大并发下载数
  - MAX_FILE_AGE_HOURS=24         # 文件最大保留时间（小时）
  - LOG_LEVEL=info                # 日志级别
```

## 卷挂载

以下目录会被挂载到宿主机：

- `./downloads` → 下载的包文件
- `./logs` → 应用日志

## 健康检查

容器包含健康检查，每 30 秒检查一次服务状态：

```bash
docker inspect --format='{{.State.Health.Status}}' <container_id>
```

## 测试

运行完整的部署测试：

```bash
./test_docker.sh
```

该脚本会：
1. 检查 Docker 服务
2. 构建镜像
3. 启动服务
4. 执行健康检查
5. 显示日志和状态

## 常用命令

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行
docker-compose logs --tail=100
```

### 重启服务

```bash
docker-compose restart
```

### 进入容器

```bash
docker-compose exec web bash
```

### 清理

```bash
# 停止并删除容器
docker-compose down

# 删除卷（注意：会删除下载的文件）
docker-compose down -v
```

## 故障排查

### 镜像构建失败

检查网络连接，确保可以访问 Docker Hub：

```bash
docker pull python:3.11-slim
```

### 服务无法启动

查看详细日志：

```bash
docker-compose logs web
```

### 健康检查失败

检查服务是否正常响应：

```bash
curl -v http://localhost:8000/api/health
```

## 生产环境建议

1. **使用特定的镜像标签**：将 `python:3.11-slim` 改为具体版本如 `python:3.11.7-slim`
2. **配置日志轮转**：添加日志驱动配置
3. **设置资源限制**：在 docker-compose.yml 中添加 CPU 和内存限制
4. **使用环境变量文件**：创建 `.env` 文件管理敏感配置
5. **启用 TLS**：配置 HTTPS 证书

## 示例：生产环境配置

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    environment:
      - MAX_CONCURRENT_DOWNLOADS=5
      - MAX_FILE_AGE_HOURS=48
      - LOG_LEVEL=warning
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 更多信息

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 README](../README.md)
