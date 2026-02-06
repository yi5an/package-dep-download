# 离线软件包下载 Web 服务

自动解析并下载 RPM/DEB 包及其依赖的 Web 服务。

## 快速开始

### Docker 部署 (推荐)

```bash
docker-compose up -d
```

访问: http://localhost:8000

### 本地运行

```bash
pip install -r requirements.txt
python backend/main.py
```

## 功能特性

- ✅ 支持 RPM 系统 (CentOS/RHEL/Fedora)
- ✅ 支持 DEB 系统 (Debian/Ubuntu)
- ✅ 自动解析并下载所有依赖
- ✅ 实时下载进度反馈
- ✅ 多线程下载加速
- ✅ 自动打包成 tar.gz

## 使用说明

1. 选择系统类型和发行版
2. 输入包名 (支持多个)
3. 点击"开始下载"
4. 等待完成后自动下载压缩包

## API 文档

访问 http://localhost:8000/docs 查看 Swagger API 文档

## 技术栈

- 后端: FastAPI + Python 3.11
- 前端: 原生 JavaScript + CSS3
- 下载: 多线程 HTTP 下载器

## 许可证

MIT License
