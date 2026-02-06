# 部署方案

## 部署选项

### 方案 1: 直接运行 (开发环境)

```bash
# 1. 安装依赖
pip install fastapi uvicorn requests

# 2. 创建必要的目录
mkdir -p downloads logs

# 3. 启动服务
python backend/app.py

# 或使用 uvicorn
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

访问: `http://localhost:8000`

### 方案 2: Docker 部署 (推荐)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要的目录
RUN mkdir -p downloads logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    environment:
      - MAX_CONCURRENT_DOWNLOADS=3
      - MAX_FILE_AGE_HOURS=24
      - LOG_LEVEL=info
    restart: unless-stopped
```

**部署命令**:
```bash
docker-compose up -d
```

### 方案 3: Systemd 服务 (生产环境)

**service 文件**: `/etc/systemd/system/package-downloader.service`

```ini
[Unit]
Description=Offline Package Downloader
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/package-downloader
Environment="PATH=/opt/package-downloader/venv/bin"
ExecStart=/opt/package-downloader/venv/bin/uvicorn backend.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启动服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable package-downloader
sudo systemctl start package-downloader
sudo systemctl status package-downloader
```

### 方案 4: Nginx 反向代理 (生产环境推荐)

**Nginx 配置**: `/etc/nginx/sites-available/package-downloader`

```nginx
upstream package_downloader {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name packages.example.com;

    client_max_body_size 1G;

    location / {
        proxy_pass http://package_downloader;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }

    # 静态文件直接由 Nginx 提供
    location /downloads/ {
        alias /opt/package-downloader/downloads/;
        autoindex off;
    }

    # 日志
    access_log /var/log/nginx/package-downloader-access.log;
    error_log /var/log/nginx/package-downloader-error.log;
}
```

**启用配置**:
```bash
sudo ln -s /etc/nginx/sites-available/package-downloader \
          /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 环境变量

创建 `.env` 文件:

```bash
# 服务配置
HOST=0.0.0.0
PORT=8000
WORKERS=4

# 下载配置
MAX_CONCURRENT_DOWNLOADS=3
DOWNLOAD_TIMEOUT=3600
MAX_FILE_AGE_HOURS=24

# 存储配置
DOWNLOAD_DIR=./downloads
LOG_DIR=./logs

# 安全配置
API_TOKEN=your-secret-token-here
ALLOWED_ORIGINS=*

# 日志配置
LOG_LEVEL=info
LOG_FORMAT=json
```

## 健康检查

### 健康检查端点

**GET** `/api/health`

```json
{
    "status": "healthy",
    "timestamp": "2024-02-06T15:30:00Z",
    "uptime": 12345,
    "active_downloads": 2,
    "total_tasks": 45,
    "disk_usage": {
        "total": "100 GB",
        "used": "25 GB",
        "free": "75 GB"
    }
}
```

### Docker 健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
```

## 日志管理

### 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/app.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
```

### 日志轮转

使用 logrotate:

```bash
# /etc/logrotate.d/package-downloader
/opt/package-downloader/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload package-downloader
    endscript
}
```

## 监控

### Prometheus 监控 (可选)

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

访问指标: `http://localhost:8000/metrics`

### 自定义监控

```python
@app.get("/api/stats")
async def get_stats():
    return {
        "total_downloads": len([t for t in tasks if t.status == "completed"]),
        "active_downloads": len([t for t in tasks if t.status == "running"]),
        "failed_downloads": len([t for t in tasks if t.status == "failed"]),
        "total_storage": sum(t.size for t in tasks),
        "uptime": time.time() - start_time
    }
```

## 备份与恢复

### 数据备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/package-downloader"
DATE=$(date +%Y%m%d-%H%M%S)

# 备份数据
tar -czf "$BACKUP_DIR/data-$DATE.tar.gz" \
    /opt/package-downloader/downloads \
    /opt/package-downloader/logs

# 保留最近 7 天的备份
find "$BACKUP_DIR" -name "data-*.tar.gz" -mtime +7 -delete
```

### 定时备份

```bash
# 添加到 crontab
0 2 * * * /opt/package-downloader/scripts/backup.sh
```

## 性能优化

### 1. 启用缓存

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

FastAPICache.init(RedisBackend(redis), prefix="package-cache")
```

### 2. 数据库优化

使用 SQLite 存储任务历史:

```python
import sqlite3

conn = sqlite3.connect('tasks.db', check_same_thread=False)
# 创建索引
conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
conn.execute('CREATE INDEX IF NOT EXISTS idx_created ON tasks(created_at)')
```

### 3. CDN 加速 (可选)

将下载文件上传到 CDN:

```python
async def upload_to_cdn(filepath: str):
    # 上传到阿里云 OSS / AWS S3
    import oss2
    auth = oss2.Auth(os.getenv('OSS_KEY'), os.getenv('OSS_SECRET'))
    bucket = oss2.Bucket(auth, 'endpoint', 'bucket-name')
    bucket.put_object_from_file(os.path.basename(filepath), filepath)
```

部署方案设计完成,是否继续最后一部分?
