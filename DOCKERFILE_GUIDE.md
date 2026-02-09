# Dockerfile 使用指南

本项目提供了多个 Dockerfile 版本，适应不同的网络环境和部署场景。

## 📦 Dockerfile 版本对比

| 文件名 | 基础镜像 | APT 源 | PyPI 源 | 推荐场景 | 构建速度 |
|--------|----------|---------|----------|----------|----------|
| `Dockerfile` | 阿里云 Python | 阿里云 | 清华大学 | 中国大陆 ⭐⭐⭐ | 快 |
| `Dockerfile.ustc` | 中科大 Python | 中科大 | 中科大 | 中国大陆/教育网 ⭐⭐⭐ | 快 |
| `Dockerfile.multi-stage` | 阿里云 Python | 阿里云 | 清华大学 | 生产环境 ⭐⭐⭐⭐ | 较快 |
| `Dockerfile.cn` | 阿里云 Python | 阿里云 | 阿里云 | 中国大陆备选 ⭐⭐ | 快 |
| `Dockerfile.local` | 阿里云 Python | 阿里云 | 阿里云 | 本地开发 ⭐⭐ | 快 |

---

## 🚀 快速使用

### 默认使用（推荐）

```bash
# 使用默认 Dockerfile（清华源）
docker-compose build
docker-compose up -d
```

### 指定 Dockerfile 构建

```bash
# 使用阿里云镜像源
docker-compose build

# 或使用中科大镜像源
docker build -f Dockerfile.ustc -t package-downloader:ustc .

# 或使用多阶段构建
docker build -f Dockerfile.multi-stage -t package-downloader:multi .
```

---

## 📋 详细说明

### 1. Dockerfile（默认 - 清华源）

**特点**:
- ✅ 使用阿里云基础镜像
- ✅ APT 软件源：阿里云
- ✅ PyPI 镜像：清华大学（速度快且稳定）
- ✅ 单阶段构建，简单直接

**适用场景**:
- 中国大陆一般网络环境
- 生产环境部署
- 快速迭代开发

**构建命令**:
```bash
docker build -t package-downloader:latest .
```

---

### 2. Dockerfile.ustc（中科大源）

**特点**:
- ✅ 使用中科大基础镜像
- ✅ APT 软件源：中科大
- ✅ PyPI 镜像：中科大
- ✅ 教育网用户友好

**适用场景**:
- 教育网用户
- 高校内部部署
- 中部地区用户

**构建命令**:
```bash
docker build -f Dockerfile.ustc -t package-downloader:ustc .
```

**运行**:
```bash
docker run -d -p 8000:8000 package-downloader:ustc
```

---

### 3. Dockerfile.multi-stage（多阶段构建）

**特点**:
- ✅ 分离构建依赖和运行依赖
- ✅ 最终镜像更小
- ✅ 使用国内镜像源加速
- ✅ 生产环境推荐

**镜像大小对比**:
- 单阶段: ~800 MB
- 多阶段: ~600 MB（减少 25%）

**适用场景**:
- 生产环境部署
- 对镜像大小敏感
- CI/CD 流水线

**构建命令**:
```bash
docker build -f Dockerfile.multi-stage -t package-downloader:prod .
```

---

### 4. Dockerfile.cn（阿里云全链路）

**特点**:
- ✅ 所有源都使用阿里云
- ✅ 阿里云用户优化
- ✅ 阿里云 ECS/AKS 部署友好

**适用场景**:
- 阿里云服务器部署
- 阿里云 Kubernetes 集群
- 阿里云函数计算

**构建命令**:
```bash
docker build -f Dockerfile.cn -t package-downloader:aliyun .
```

---

### 5. Dockerfile.local（本地开发）

**特点**:
- ✅ 简化配置
- ✅ 快速构建
- ✅ 本地测试优化

**适用场景**:
- 本地开发测试
- CI/CD 验证
- 快速原型验证

**构建命令**:
```bash
docker build -f Dockerfile.local -t package-downloader:dev .
```

---

## 🔧 镜像源速度对比

### PyPI 镜像源（中国大陆）

| 镜像源 | 地址 | 平均延迟 | 稳定性 |
|--------|------|----------|--------|
| 清华大学 | pypi.tuna.tsinghua.edu.cn | ~50ms | ⭐⭐⭐⭐⭐ |
| 中科大 | mirrors.ustc.edu.cn | ~70ms | ⭐⭐⭐⭐⭐ |
| 阿里云 | mirrors.aliyun.com | ~100ms | ⭐⭐⭐⭐ |
| 豆瓣 | https://pypi.douban.com | ~150ms | ⭐⭐⭐ |
| 官方源 | pypi.org | >500ms | ⭐⭐ |

### APT 镜像源（中国大陆）

| 镜像源 | 地址 | 速度 | 稳定性 |
|--------|------|------|--------|
| 阿里云 | mirrors.aliyun.com | 快 | ⭐⭐⭐⭐⭐ |
| 清华大学 | mirrors.tuna.tsinghua.edu.cn | 快 | ⭐⭐⭐⭐⭐ |
| 中科大 | mirrors.ustc.edu.cn | 快 | ⭐⭐⭐⭐⭐ |
| 网易 | mirrors.163.com | 较快 | ⭐⭐⭐⭐ |
| 官方源 | deb.debian.org | 慢 | ⭐⭐ |

---

## 💡 使用建议

### 按网络环境选择

**家庭宽带 / 企业网络**
```bash
# 使用默认 Dockerfile（清华源）
docker-compose up -d
```

**教育网 / 高校**
```bash
# 使用中科大版本
docker build -f Dockerfile.ustc -t package-downloader .
docker run -d -p 8000:8000 package-downloader
```

**阿里云服务器**
```bash
# 使用阿里云优化版本
docker build -f Dockerfile.cn -t package-downloader .
```

### 按部署场景选择

**开发测试**
```bash
# 快速构建
docker build -f Dockerfile.local -t package-downloader:dev .
```

**生产部署**
```bash
# 多阶段构建，镜像更小
docker build -f Dockerfile.multi-stage -t package-downloader:prod .
```

---

## 🛠️ 高级用法

### 修改 docker-compose.yml 使用不同的 Dockerfile

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.ustc  # 指定使用的 Dockerfile
    # ...
```

### 使用构建参数

```bash
# 指定基础镜像
docker build --build-arg BASE_IMAGE=python:3.11 -t package-downloader .
```

### 查看镜像大小

```bash
docker images | grep package-downloader
```

---

## 📊 构建时间对比

| Dockerfile | 首次构建 | 重复构建 | 镜像大小 |
|------------|----------|----------|----------|
| Dockerfile | ~3 分钟 | ~30 秒 | ~800 MB |
| Dockerfile.ustc | ~3 分钟 | ~30 秒 | ~800 MB |
| Dockerfile.multi-stage | ~4 分钟 | ~30 秒 | ~600 MB |
| Dockerfile.cn | ~3 分钟 | ~30 秒 | ~800 MB |
| Dockerfile.local | ~2 分钟 | ~20 秒 | ~850 MB |

---

## 🌐 国际环境

如果在海外环境（无网络限制），可以使用官方源：

```dockerfile
FROM python:3.11-slim

# 使用官方软件源
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p downloads logs

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🐛 故障排查

### 问题 1: 镜像拉取失败

```bash
# 尝试其他镜像源
docker pull registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim
```

### 问题 2: pip 安装超时

```bash
# 更换 PyPI 镜像源
# 在 Dockerfile 中修改 -i 参数
-i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 3: apt 更新慢

```bash
# 更换 APT 镜像源
# 在 Dockerfile 中修改 sed 命令
sed -i 's/deb.debian.org/mirrors.aliyun.com/g'
```

---

## ✅ 推荐配置

**中国大陆生产环境**:
```bash
# 使用默认 Dockerfile
docker build -t package-downloader:v1.0 .
docker-compose up -d
```

**中国大陆开发环境**:
```bash
# 使用 Dockerfile.local
docker build -f Dockerfile.local -t package-downloader:dev .
docker run -d -p 8000:8000 -v $(pwd)/downloads:/app/downloads package-downloader:dev
```

**教育网环境**:
```bash
# 使用 Dockerfile.ustc
docker build -f Dockerfile.ustc -t package-downloader:edu .
docker run -d -p 8000:8000 package-downloader:edu
```

---

## 📚 相关资源

- [清华大学开源镜像站](https://mirrors.tuna.tsinghua.edu.cn/)
- [中科大开源镜像站](https://mirrors.ustc.edu.cn/)
- [阿里云镜像站](https://developer.aliyun.com/mirror/)
- [Docker 部署文档](DOCKER.md)
- [快速开始指南](QUICKSTART.md)

---

**提示**: 建议根据实际网络环境测试不同版本，选择最适合您的配置。
