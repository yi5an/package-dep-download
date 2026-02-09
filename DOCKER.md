# Docker 部署指南

本文档介绍如何使用 Docker 部署离线软件包下载工具。

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yi5an/package-dep-download.git
cd package-dep-download
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 根据需要编辑 .env 文件
```

### 3. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 访问服务

服务启动后，访问: http://localhost:8000

## 配置选项

### 环境变量

在 `.env` 文件中配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | 0.0.0.0 | 监听地址 |
| `PORT` | 8000 | 容器内端口 |
| `HOST_PORT` | 8000 | 主机端口 |
| `MAX_CONCURRENT_DOWNLOADS` | 3 | 最大并发下载数 |
| `MAX_FILE_AGE_HOURS` | 24 | 文件保留时间（小时） |
| `DOWNLOAD_DIR` | /app/downloads | 下载目录 |
| `LOG_DIR` | /app/logs | 日志目录 |

### 端口映射

默认映射: `8000:8000`

修改主机端口:
```yaml
# docker-compose.yml
ports:
  - "8080:8000"  # 使用主机 8080 端口
```

或在 `.env` 中:
```bash
HOST_PORT=8080
```

## 数据持久化

默认使用 Docker volumes 持久化数据:

- `./downloads` → 容器内 `/app/downloads`
- `./logs` → 容器内 `/app/logs`

## 生产环境部署

### 使用 Nginx 反向代理

1. 创建 `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream package_downloader {
        server web:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://package_downloader;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

2. 更新 `docker-compose.yml`:

```yaml
services:
  web:
    # ... 现有配置 ...

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - web
    restart: unless-stopped
```

### 使用 HTTPS (Let's Encrypt)

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - web
    restart: unless-stopped
```

### 资源限制

在 `docker-compose.yml` 中添加资源限制:

```yaml
services:
  web:
    # ... 现有配置 ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 监控和维护

### 查看日志

```bash
# 查看所有日志
docker-compose logs

# 查看实时日志
docker-compose logs -f

# 查看最近 100 行
docker-compose logs --tail=100
```

### 查看容器状态

```bash
# 查看运行状态
docker-compose ps

# 进入容器
docker-compose exec web bash

# 查看资源使用
docker stats
```

### 备份数据

```bash
# 备份下载目录
tar -czf downloads-backup-$(date +%Y%m%d).tar.gz downloads/

# 备份日志
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### 清理旧文件

```bash
# 进入容器清理
docker-compose exec web find /app/downloads -name "*.tar.gz" -mtime +7 -delete

# 或在主机上
find ./downloads -name "*.tar.gz" -mtime +7 -delete
```

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs web

# 检查端口占用
netstat -tulpn | grep 8000

# 重建容器
docker-compose down
docker-compose up -d --build
```

### 健康检查失败

```bash
# 手动检查健康状态
docker-compose exec web python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# 查看容器进程
docker-compose exec web ps aux
```

### 性能优化

```bash
# 增加并发下载
# 在 .env 中设置
MAX_CONCURRENT_DOWNLOADS=5

# 重启服务应用配置
docker-compose restart web
```

## 更新部署

```bash
# 拉取最新代码
git pull origin master

# 重建并重启
docker-compose down
docker-compose up -d --build

# 或使用滚动更新（零停机）
docker-compose up -d --no-deps --build web
```

## 安全建议

1. **不要以 root 运行**: Dockerfile 已配置非 root 用户
2. **限制资源**: 设置 CPU 和内存限制
3. **使用 HTTPS**: 生产环境必须启用 HTTPS
4. **定期更新**: 及时更新基础镜像和依赖
5. **备份**: 定期备份下载目录和日志
6. **监控**: 设置日志监控和告警

## 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除数据卷
docker-compose down -v

# 删除镜像
docker rmi package-dep-download-web
```

## 支持

如有问题，请访问: https://github.com/yi5an/package-dep-download/issues
