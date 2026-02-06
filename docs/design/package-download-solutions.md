# 软件包下载方案对比

## 方案一:使用 Python 库解析依赖(推荐)

### RPM 系统
```python
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

# 从镜像站下载 repodata
base_url = "https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/"
repomd = requests.get(urljoin(base_url, "repodata/repomd.xml")).text

# 解析包元数据
# 获取依赖关系
# 递归下载 .rpm 文件
```

**优点**:
- ✅ 纯 Python 实现,无外部依赖
- ✅ 直接从镜像站下载,速度快
- ✅ 完全可控,易调试

**缺点**:
- ❌ 需要解析 XML 格式的 repodata
- ❌ 不同发行版格式略有差异

### DEB 系统
```python
import requests
import gzip

# 下载 Packages.gz
packages_url = "http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz"
packages = gzip.decompress(requests.get(packages_url).content).decode()

# 解析包信息
# 提取 Depends 字段
# 递归下载 .deb 文件
```

**优点**:
- ✅ Packages 格式简单易解析
- ✅ 纯文本格式,处理方便

**缺点**:
- ❌ 文件较大(几十MB),下载和解析耗时

---

## 方案二:调用系统工具

### RPM 系统
```python
import subprocess

# 使用 dnf/yum 下载
subprocess.run([
    "dnf", "download",
    "--resolve",  # 解析依赖
    "--destdir=output",
    "nginx"
])
```

**优点**:
- ✅ 利用现成工具,开发快
- ✅ 依赖解析准确

**缺点**:
- ❌ 依赖系统命令
- ❌ 无法在容器中运行(除非安装完整系统)

### DEB 系统
```python
import subprocess

# 使用 apt-get download
subprocess.run([
    "apt-get", "download",
    "-o", "Dir::Cache::Archives=/tmp",
    "nginx"
])
```

**缺点同上**

---

## 方案三:使用第三方库(最佳)

### libsolv Python 绑定
```python
import libsolv

# 创建仓库
pool = libsolv.Pool()
repo = pool.add_repo("centos-8")

# 添加包
# 解析依赖
# 生成下载列表
```

**优点**:
- ✅ 专业级依赖解析器
- ✅ 性能极高
- ✅ 被 dnf/zypper 使用

**缺点**:
- ❌ 需要安装 libsolv
- ❌ Python 绑定文档较少

---

## 方案四:镜像站 REST API(最简单)

### 使用 Reprepro API 或类似服务
```python
import requests

# 某些镜像站提供 API
api_url = "https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/Packages/"

response = requests.get(f"{api_url}?search=nginx")
# 解析返回的 JSON
# 下载 .rpm 文件
```

**优点**:
- ✅ 简单直接

**缺点**:
- ❌ 大多数镜像站不提供 API
- ❌ 依赖依赖关系仍需解析

---

## 推荐方案:混合方案

结合方案一和方案二的优势:

1. **对于 RPM 系统**:
   - 使用 `dnf download --resolve` (如果有 dnf)
   - 或解析 repodata XML (纯 Python 方案)

2. **对于 DEB 系统**:
   - 解析 Packages.gz (纯 Python 方案)
   - 或使用 `apt-rdepends` (如果有 apt)

3. **下载层**:
   - 直接从镜像站 HTTP 下载
   - 使用 requests 库,支持断点续传
   - 多线程下载加速

## 具体实现架构

```
┌─────────────────────────────────────────┐
│          包下载管理器                     │
│  ┌────────────┐  ┌──────────────┐       │
│  │ RPM 下载器  │  │ DEB 下载器   │       │
│  └────────────┘  └──────────────┘       │
│         ↓              ↓                 │
│  ┌──────────────────────────────┐       │
│  │     依赖解析引擎              │       │
│  │  - repodata 解析器 (RPM)     │       │
│  │  - Packages 解析器 (DEB)     │       │
│  └──────────────────────────────┘       │
│         ↓                                 │
│  ┌──────────────────────────────┐       │
│  │     HTTP 下载器               │       │
│  │  - 多线程下载                 │       │
│  │  - 断点续传                   │       │
│  │  - 镜像站切换                 │       │
│  └──────────────────────────────┘       │
└─────────────────────────────────────────┘
```

## 我的推荐

**推荐使用方案一的改进版**:

1. **RPM 系统**: 解析 repodata + 直接 HTTP 下载
   - 使用 `createrepo_c` 库解析 repodata
   - 或用纯 Python 解析 XML

2. **DEB 系统**: 解析 Packages.gz + 直接 HTTP 下载
   - 纯文本解析,简单高效

3. **备用方案**: 如果系统有 dnf/apt,可以调用它们下载

这样可以:
- ✅ 不依赖系统命令
- ✅ 容器友好
- ✅ 完全可控
- ✅ 支持跨平台下载(在 x86_64 上为 aarch64 下载)
