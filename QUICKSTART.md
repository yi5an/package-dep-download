# 快速开始指南

## 本地开发运行

### 方法 1: 直接运行（推荐）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
./start.sh

# 或手动启动
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

访问: http://localhost:8000

### 方法 2: Docker 部署

#### 前置条件

1. 安装 Docker 和 Docker Compose
2. 配置 Docker 镜像加速（可选，但推荐）

#### 配置 Docker 镜像加速

**方式 1: 使用配置脚本（推荐）**
```bash
sudo bash setup-docker-mirror.sh
```

**方式 2: 手动配置**
```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 快速启动

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 构建并启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

#### 国内网络环境

如果遇到 Docker Hub 连接问题：

**选项 A: 预先拉取镜像**
```bash
# 从其他来源获取 python:3.11-slim 镜像
# 然后正常构建
docker-compose build
```

**选项 B: 使用代理**
```bash
# 配置 Docker 代理
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy:port"
Environment="HTTPS_PROXY=http://your-proxy:port"
Environment="NO_PROXY=localhost,127.0.0.1"
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 测试部署

```bash
# 运行自动化测试
bash test-docker-compose.sh
```

该脚本会：
1. 检查 Docker 环境
2. 构建镜像
3. 启动服务
4. 执行健康检查
5. 运行功能测试
6. 显示访问信息

#### 访问服务

服务启动后访问: http://localhost:8000

#### 管理命令

```bash
# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 进入容器
docker-compose exec web bash

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 删除数据卷
docker-compose down -v
```

## 生产环境部署

详见 DOCKER.md

## 故障排查

### 问题 1: 端口已被占用

```bash
# 查看端口占用
sudo netstat -tulpn | grep 8000

# 修改端口
# 编辑 .env 文件
HOST_PORT=8080
```

### 问题 2: 容器无法启动

```bash
# 查看详细日志
docker-compose logs web

# 重建容器
docker-compose down
docker-compose up -d --build
```

### 问题 3: 健康检查失败

```bash
# 手动检查
curl http://localhost:8000/api/health

# 查看容器进程
docker-compose exec web ps aux
```

### 问题 4: 下载失败

```bash
# 检查磁盘空间
df -h

# 检查目录权限
ls -la downloads/

# 查看错误日志
docker-compose logs web | grep -i error
```

## 获取帮助

- GitHub Issues: https://github.com/yi5an/package-dep-download/issues
- Docker 部署文档: DOCKER.md
- 技术文档: README.md
