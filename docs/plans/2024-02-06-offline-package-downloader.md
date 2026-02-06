# 离线软件包下载 Web 服务实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个带 Web 界面的离线软件包下载服务,用户输入包名后,系统自动解析依赖并从镜像站直接下载,最后生成压缩包供下载。

**Architecture:**
- 后端: FastAPI + Python 3.11,纯 Python 实现依赖解析(不依赖系统命令)
- 前端: 原生 JavaScript + Server-Sent Events 实时进度推送
- 下载层: 多线程 HTTP 下载器,支持断点续传和镜像站故障切换

**Tech Stack:**
- FastAPI 0.100+, uvicorn, requests, Pydantic
- 原生 JavaScript ES6+, CSS3, SSE
- Docker, Docker Compose

---

## Phase 1: 项目基础设置 (30 分钟)

### Task 1.1: 创建项目结构和配置文件

**Files:**
- Create: `requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/config.py`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: 创建 requirements.txt**

```bash
cat > requirements.txt << 'EOF'
# FastAPI 和服务器
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# HTTP 客户端
requests==2.31.0
aiohttp==3.9.1

# 工具库
python-dotenv==1.0.0

# 测试
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2

# 代码质量
black==23.12.0
flake8==6.1.0
mypy==1.7.1
EOF
```

**Step 2: 创建后端配置模块**

```python
# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 服务配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))

    # 下载配置
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "3600"))
    MAX_FILE_AGE_HOURS: int = int(os.getenv("MAX_FILE_AGE_HOURS", "24"))

    # 存储路径
    BASE_DIR: Path = Path(__file__).parent.parent
    DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", BASE_DIR / "downloads"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))

    # 镜像站配置
    MIRRORS = {
        "aliyun": "https://mirrors.aliyun.com",
        "tsinghua": "https://mirrors.tuna.tsinghua.edu.cn",
        "ustc": "https://mirrors.ustc.edu.cn",
    }

    # 发行版配置
    DISTRIBUTIONS = {
        "centos-7": {
            "type": "rpm",
            "name": "CentOS 7",
            "baseos": "https://mirrors.aliyun.com/centos/7/os/x86_64/",
            "updates": "https://mirrors.aliyun.com/centos/7/updates/x86_64/",
        },
        "centos-8": {
            "type": "rpm",
            "name": "CentOS 8",
            "baseos": "https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/",
            "appstream": "https://mirrors.aliyun.com/centos/8/AppStream/x86_64/os/",
        },
        "ubuntu-22": {
            "type": "deb",
            "name": "Ubuntu 22.04 LTS",
            "main": "http://archive.ubuntu.com/ubuntu/dists/jammy/main/",
            "universe": "http://archive.ubuntu.com/ubuntu/dists/jammy/universe/",
        },
    }

    # 确保目录存在
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

config = Config()
```

**Step 3: 创建环境变量示例**

```bash
cat > .env.example << 'EOF'
# 服务配置
HOST=0.0.0.0
PORT=8000
WORKERS=1

# 下载配置
MAX_CONCURRENT_DOWNLOADS=3
DOWNLOAD_TIMEOUT=3600
MAX_FILE_AGE_HOURS=24

# 存储配置
DOWNLOAD_DIR=./downloads
LOG_DIR=./logs

# 安全配置 (可选)
# API_TOKEN=your-secret-token-here
EOF
```

**Step 4: 创建 .gitignore**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# 下载文件
downloads/
*.tar.gz
*.rpm
*.deb

# 日志
logs/
*.log

# 环境变量
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# 测试
.pytest_cache/
.coverage
htmlcov/

# macOS
.DS_Store

# 临时文件
*.tmp
*.bak
EOF
```

**Step 5: 安装依赖**

```bash
pip install -r requirements.txt
```

**Step 6: 验证安装**

```bash
python -c "import fastapi; import uvicorn; print('Dependencies installed successfully')"
```

预期输出: `Dependencies installed successfully`

**Step 7: 提交**

```bash
git add requirements.txt backend/config.py .env.example .gitignore
git commit -m "chore: set up project structure and configuration"
```

---

## Phase 2: RPM 依赖解析器 (2 小时)

### Task 2.1: 创建 RPM repodata 解析器基础

**Files:**
- Create: `backend/resolvers/__init__.py`
- Create: `backend/resolvers/rpm.py`
- Create: `tests/test_rpm_resolver.py`

**Step 1: 编写测试 - repodata 加载**

```python
# tests/test_rpm_resolver.py
import pytest
from backend.resolvers.rpm import RPMRepodataParser

@pytest.fixture
def rpm_parser():
    return RPMRepodataParser(
        mirror_url="https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/"
    )

def test_load_metadata(rpm_parser):
    """测试加载 repomd.xml"""
    rpm_parser.load_metadata()
    assert rpm_parser.primary_xml is not None
    assert len(rpm_parser.primary_xml) > 0

def test_parse_packages(rpm_parser):
    """测试解析包信息"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    assert len(rpm_parser.package_cache) > 0
    assert "bash" in rpm_parser.package_cache

    bash_pkg = rpm_parser.package_cache["bash"]
    assert "version" in bash_pkg
    assert "url" in bash_pkg
    assert "requires" in bash_pkg

def test_find_package(rpm_parser):
    """测试查找特定包"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    pkg = rpm_parser.find_package("bash")
    assert pkg is not None
    assert pkg["name"] == "bash"

def test_package_not_found(rpm_parser):
    """测试不存在的包"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    pkg = rpm_parser.find_package("nonexistent-package-xyz")
    assert pkg is None
```

**Step 2: 运行测试 (预期失败)**

```bash
pytest tests/test_rpm_resolver.py -v
```

预期: `ModuleNotFoundError: No module named 'backend.resolvers.rpm'`

**Step 3: 实现解析器**

```python
# backend/resolvers/rpm.py
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import requests
import gzip
from io import BytesIO

class RPMRepodataParser:
    """RPM repodata 解析器"""

    def __init__(self, mirror_url: str):
        self.mirror_url = mirror_url.rstrip("/") + "/"
        self.primary_xml = None
        self.package_cache = {}

    def load_metadata(self):
        """加载 repomd.xml 并获取 primary.xml.gz"""
        repomd_url = urljoin(self.mirror_url, "repodata/repomd.xml")

        response = requests.get(repomd_url, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # 查找 primary 数据
        ns = {"repo": "http://linux.duke.edu/metadata/repo"}
        primary_elements = root.findall(".//repo:data[@type='primary']", ns)

        if not primary_elements:
            raise ValueError("Primary metadata not found in repomd.xml")

        for primary_elem in primary_elements:
            location = primary_elem.find("repo:location", ns)
            if location is not None:
                primary_path = location.get("href")
                self.primary_xml = self._download_and_decompress(
                    urljoin(self.mirror_url, primary_path)
                )
                break

    def _download_and_decompress(self, url: str) -> str:
        """下载并解压 XML 文件"""
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        if url.endswith(".gz"):
            decompressed = gzip.decompress(response.content)
            return decompressed.decode("utf-8")
        else:
            return response.content.decode("utf-8")

    def parse_packages(self):
        """解析所有包信息"""
        if not self.primary_xml:
            raise ValueError("Metadata not loaded. Call load_metadata() first.")

        root = ET.fromstring(self.primary_xml)

        ns = {
            "common": "http://linux.duke.edu/metadata/common",
            "rpm": "http://linux.duke.edu/metadata/rpm"
        }

        for pkg in root.findall(".//common:package", ns):
            try:
                name_elem = pkg.find("common:name", ns)
                if name_elem is None:
                    continue

                name = name_elem.text
                if not name:
                    continue

                arch_elem = pkg.find("common:arch", ns)
                arch = arch_elem.text if arch_elem is not None else "x86_64"

                version_elem = pkg.find("common:version", ns)
                version = version_elem.get("ver") if version_elem is not None else "unknown"

                location_elem = pkg.find("common:location", ns)
                if location_elem is None:
                    continue

                href = location_elem.get("href")
                url = urljoin(self.mirror_url, href)

                # 解析依赖
                requires = []
                for req in pkg.findall(".//rpm:entry", ns):
                    req_name = req.get("name")
                    if req_name and not req_name.startswith("rpmlib("):
                        requires.append(req_name)

                self.package_cache[name] = {
                    "name": name,
                    "version": version,
                    "arch": arch,
                    "url": url,
                    "requires": requires
                }
            except Exception as e:
                # 跳过解析失败的包
                continue

    def find_package(self, name: str):
        """查找特定包"""
        return self.package_cache.get(name)
```

**Step 4: 运行测试 (预期部分通过)**

```bash
pytest tests/test_rpm_resolver.py::test_load_metadata -v
```

预期: PASS (需要网络连接)

**Step 5: 运行所有测试**

```bash
pytest tests/test_rpm_resolver.py -v
```

**Step 6: 提交**

```bash
git add backend/resolvers/ tests/test_rpm_resolver.py
git commit -m "feat: implement RPM repodata parser"
```

---

### Task 2.2: 实现 RPM 依赖解析

**Files:**
- Modify: `backend/resolvers/rpm.py`
- Modify: `tests/test_rpm_resolver.py`

**Step 1: 编写依赖解析测试**

```python
# 添加到 tests/test_rpm_resolver.py

def test_resolve_simple_package(rpm_parser):
    """测试解析单个包"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    from backend.resolvers.rpm import RPMDependencyResolver
    resolver = RPMDependencyResolver(rpm_parser)

    packages = resolver.resolve("bash")

    assert len(packages) > 0
    assert any(p["name"] == "bash" for p in packages)

def test_resolve_with_dependencies(rpm_parser):
    """测试解析带依赖的包"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    from backend.resolvers.rpm import RPMDependencyResolver
    resolver = RPMDependencyResolver(rpm_parser)

    packages = resolver.resolve("coreutils")

    # coreutils 应该有依赖
    assert len(packages) >= 1

def test_avoid_duplicates(rpm_parser):
    """测试避免重复解析"""
    rpm_parser.load_metadata()
    rpm_parser.parse_packages()

    from backend.resolvers.rpm import RPMDependencyResolver
    resolver = RPMDependencyResolver(rpm_parser)

    packages = resolver.resolve("bash")

    # 检查没有重复的包
    names = [p["name"] for p in packages]
    assert len(names) == len(set(names))
```

**Step 2: 运行测试 (预期失败)**

```bash
pytest tests/test_rpm_resolver.py::test_resolve_simple_package -v
```

预期: `ImportError: cannot import name 'RPMDependencyResolver'`

**Step 3: 实现依赖解析器**

```python
# 添加到 backend/resolvers/rpm.py

class RPMDependencyResolver:
    """RPM 依赖解析器"""

    def __init__(self, parser: RPMRepodataParser):
        self.parser = parser
        self.resolved = set()

    def resolve(self, package_name: str) -> list:
        """
        递归解析包及其所有依赖

        返回: 包列表 (包含输入包和所有依赖)
        """
        if package_name in self.resolved:
            return []

        pkg = self.parser.find_package(package_name)
        if not pkg:
            raise ValueError(f"Package '{package_name}' not found")

        packages = [pkg]
        self.resolved.add(package_name)

        # 递归解析依赖
        for req in pkg.get("requires", []):
            # 跳过以 / 开头的文件依赖
            if not req or req.startswith("/"):
                continue

            # 跳过 rpmlib 依赖
            if req.startswith("rpmlib("):
                continue

            # 递归解析
            try:
                dep_packages = self.resolve(req)
                packages.extend(dep_packages)
            except ValueError:
                # 依赖包不存在,跳过
                continue

        return packages

    def get_download_list(self, packages: list) -> list:
        """
        获取去重的下载列表

        返回: URL 列表
        """
        seen = set()
        download_list = []

        for pkg in packages:
            url = pkg.get("url")
            if url and url not in seen:
                seen.add(url)
                download_list.append(pkg)

        return download_list
```

**Step 4: 运行测试**

```bash
pytest tests/test_rpm_resolver.py -v
```

**Step 5: 提交**

```bash
git add backend/resolvers/rpm.py tests/test_rpm_resolver.py
git commit -m "feat: implement RPM dependency resolver"
```

---

## Phase 3: DEB 依赖解析器 (1.5 小时)

### Task 3.1: 实现 DEB Packages 解析器

**Files:**
- Create: `backend/resolvers/deb.py`
- Create: `tests/test_deb_resolver.py`

**Step 1: 编写测试**

```python
# tests/test_deb_resolver.py
import pytest
from backend.resolvers.deb import DEBPackageParser, DEBDependencyResolver

@pytest.fixture
def deb_parser():
    return DEBPackageParser(
        mirror_url="http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/"
    )

def test_load_packages(deb_parser):
    """测试加载 Packages.gz"""
    deb_parser.load_packages()
    assert len(deb_parser.package_cache) > 0

def test_parse_package_info(deb_parser):
    """测试解析包信息"""
    deb_parser.load_packages()

    pkg = deb_parser.find_package("bash")
    assert pkg is not None
    assert pkg["Package"] == "bash"
    assert "Version" in pkg
    assert "Depends" in pkg

def test_resolve_dependencies(deb_parser):
    """测试解析依赖"""
    deb_parser.load_packages()

    resolver = DEBDependencyResolver(deb_parser)
    packages = resolver.resolve("bash")

    assert len(packages) > 0
    assert any(p["Package"] == "bash" for p in packages)
```

**Step 2: 运行测试 (预期失败)**

```bash
pytest tests/test_deb_resolver.py -v
```

**Step 3: 实现 DEB 解析器**

```python
# backend/resolvers/deb.py
import requests
import gzip
from urllib.parse import urljoin
import re

class DEBPackageParser:
    """DEB Packages.gz 解析器"""

    def __init__(self, mirror_url: str):
        self.mirror_url = mirror_url.rstrip("/") + "/"
        self.package_cache = {}

    def load_packages(self):
        """下载并解析 Packages.gz"""
        packages_url = urljoin(self.mirror_url, "Packages.gz")

        response = requests.get(packages_url, timeout=60)
        response.raise_for_status()

        # 解压
        decompressed = gzip.decompress(response.content).decode("utf-8")

        # 解析包信息
        self._parse_packages_text(decompressed)

    def _parse_packages_text(self, text: str):
        """解析 Packages 文本格式"""
        current_package = {}

        for line in text.split("\n"):
            if line.strip() == "":
                # 空行表示包信息结束
                if current_package and "Package" in current_package:
                    name = current_package["Package"]
                    self.package_cache[name] = current_package
                    current_package = {}
            elif line.startswith(" "):
                # 续行
                if current_package:
                    last_key = list(current_package.keys())[-1]
                    current_package[last_key] += "\n" + line.strip()
            elif ":" in line:
                # 新字段
                key, value = line.split(":", 1)
                current_package[key.strip()] = value.strip()

    def find_package(self, name: str):
        """查找特定包"""
        return self.package_cache.get(name)

    def get_package_url(self, package_name: str) -> str:
        """获取包的下载 URL"""
        pkg = self.find_package(package_name)
        if not pkg:
            return None

        filename = pkg.get("Filename")
        if not filename:
            return None

        # 构建完整 URL
        # mirror_url: http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/
        # filename: pool/main/b/bash/bash_5.1-2ubuntu1_amd64.deb
        base_url = self.mirror_url.split("/dists/")[0]
        return f"{base_url}/{filename}"


class DEBDependencyResolver:
    """DEB 依赖解析器"""

    def __init__(self, parser: DEBPackageParser):
        self.parser = parser
        self.resolved = set()

    def resolve(self, package_name: str) -> list:
        """
        递归解析包及其所有依赖

        返回: 包字典列表
        """
        if package_name in self.resolved:
            return []

        pkg = self.parser.find_package(package_name)
        if not pkg:
            raise ValueError(f"Package '{package_name}' not found")

        packages = [pkg]
        self.resolved.add(package_name)

        # 解析 Depends 字段
        depends_str = pkg.get("Depends", "")
        dependencies = self._parse_depends(depends_str)

        for dep in dependencies:
            try:
                dep_packages = self.resolve(dep)
                packages.extend(dep_packages)
            except ValueError:
                continue

        return packages

    def _parse_depends(self, depends_str: str) -> list:
        """
        解析 Depends 字段

        示例: "libc6 (>= 2.27), libssl1.1 (>= 1.1.1)"
        返回: ["libc6", "libssl1.1"]
        """
        if not depends_str:
            return []

        dependencies = []

        # 分割逗号分隔的依赖
        for part in depends_str.split(","):
            part = part.strip()

            # 移除版本限制 (>= 2.27), (<< 1.0) 等
            match = re.match(r'^([a-zA-Z0-9+.-]+)', part)
            if match:
                dep_name = match.group(1)
                dependencies.append(dep_name)

        return dependencies

    def get_download_list(self, packages: list) -> list:
        """
        获取去重的下载列表

        返回: 包字典列表 (包含 URL)
        """
        seen = set()
        download_list = []

        for pkg in packages:
            name = pkg.get("Package")
            if not name or name in seen:
                continue

            seen.add(name)

            # 添加下载 URL
            pkg_with_url = pkg.copy()
            pkg_with_url["url"] = self.parser.get_package_url(name)
            download_list.append(pkg_with_url)

        return download_list
```

**Step 4: 运行测试**

```bash
pytest tests/test_deb_resolver.py -v
```

**Step 5: 提交**

```bash
git add backend/resolvers/deb.py tests/test_deb_resolver.py
git commit -m "feat: implement DEB package parser and dependency resolver"
```

---

## Phase 4: HTTP 下载器 (1.5 小时)

### Task 4.1: 实现多线程下载器

**Files:**
- Create: `backend/downloaders/__init__.py`
- Create: `backend/downloaders/http.py`
- Create: `tests/test_http_downloader.py`

**Step 1: 编写测试**

```python
# tests/test_http_downloader.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from backend.downloaders.http import PackageDownloader

def test_download_single_package(tmp_path):
    """测试下载单个包"""
    downloader = PackageDownloader(max_workers=1)

    pkg = {
        "name": "test-package",
        "url": "http://example.com/test.rpm",
        "version": "1.0"
    }

    # Mock HTTP 响应
    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content = lambda chunk_size: [b"test content"]

    with patch("requests.get", return_value=mock_response):
        result = downloader._download_single(pkg, tmp_path)

    assert result.exists()
    assert result.name == "test.rpm"

def test_download_with_resume(tmp_path):
    """测试断点续传"""
    downloader = PackageDownloader(max_workers=1)

    # 创建部分下载的文件
    partial_file = tmp_path / "partial.rpm"
    partial_file.write_bytes(b"partial content")

    pkg = {
        "name": "test",
        "url": "http://example.com/test.rpm"
    }

    # Mock 响应支持 Range
    mock_response = Mock()
    mock_response.status_code = 206
    mock_response.headers = {"content-length": "20", "content-range": "bytes 15-19/20"}

    with patch("requests.get", return_value=mock_response):
        try:
            downloader._download_single(pkg, tmp_path)
        except:
            pass  # 测试是否尝试了断点续传
```

**Step 2: 运行测试 (预期失败)**

```bash
pytest tests/test_http_downloader.py -v
```

**Step 3: 实现下载器**

```python
# backend/downloaders/http.py
import os
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional

class PackageDownloader:
    """多线程包下载器"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.session = requests.Session()

    def download_packages(
        self,
        packages: List[Dict],
        output_dir: Path,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        批量下载包

        Args:
            packages: 包列表 (包含 url, name 等字段)
            output_dir: 输出目录
            progress_callback: 进度回调函数 callback(current, total, package)

        Returns:
            {"success": [...], "failed": [...], "total": int}
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "success": [],
            "failed": [],
            "total": len(packages)
        }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._download_single,
                    pkg,
                    output_dir
                ): pkg for pkg in packages
            }

            for i, future in enumerate(as_completed(futures), 1):
                pkg = futures[future]
                try:
                    filepath = future.result()
                    results["success"].append(filepath)

                    if progress_callback:
                        progress_callback(i, len(packages), pkg)

                except Exception as e:
                    results["failed"].append({
                        "package": pkg,
                        "error": str(e)
                    })

        return results

    def _download_single(self, pkg: Dict, output_dir: Path) -> Path:
        """下载单个包"""
        url = pkg.get("url")
        if not url:
            raise ValueError(f"Package {pkg.get('name')} has no URL")

        filename = os.path.basename(url)
        filepath = output_dir / filename

        # 断点续传
        if filepath.exists():
            file_size = filepath.stat().st_size
            headers = {"Range": f"bytes={file_size}-"}

            response = self.session.get(url, headers=headers, stream=True, timeout=30)

            if response.status_code == 206:  # Partial Content
                # 继续下载
                mode = "ab"
            else:
                # 不支持断点续传,重新下载
                response = self.session.get(url, stream=True, timeout=30)
                mode = "wb"
                file_size = 0
        else:
            response = self.session.get(url, stream=True, timeout=30)
            mode = "wb"
            file_size = 0

        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))

        with open(filepath, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filepath
```

**Step 4: 运行测试**

```bash
pytest tests/test_http_downloader.py -v
```

**Step 5: 提交**

```bash
git add backend/downloaders/ tests/test_http_downloader.py
git commit -m "feat: implement multi-threaded HTTP downloader"
```

---

## Phase 5: FastAPI 后端核心 (2 小时)

### Task 5.1: 创建数据模型和任务管理器

**Files:**
- Create: `backend/models.py`
- Create: `backend/task_manager.py`
- Create: `tests/test_task_manager.py`

**Step 1: 创建数据模型**

```python
# backend/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PackageRequest(BaseModel):
    """包下载请求"""
    packages: List[str] = Field(..., min_items=1, max_items=100, description="包名列表")
    system_type: str = Field(..., pattern="^(rpm|deb)$", description="系统类型")
    distribution: str = Field(..., min_length=1, description="发行版")
    arch: str = Field(default="auto", description="架构")
    deep_download: bool = Field(default=False, description="是否递归下载")

class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int = Field(default=0, ge=0, le=100)
    message: str
    packages_count: int = 0
    total_size: str = "0 MB"
    created_at: str
    completed_at: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
```

**Step 2: 创建任务管理器**

```python
# backend/task_manager.py
import uuid
import threading
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import subprocess
import tarfile

from backend.models import TaskStatus, PackageRequest
from backend.config import config

class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, TaskStatus] = {}
        self.lock = threading.Lock()
        self.active_downloads = 0

    def create_task(self, request: PackageRequest) -> TaskStatus:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]

        task = TaskStatus(
            task_id=task_id,
            status="pending",
            progress=0,
            message="任务已创建",
            created_at=datetime.now().isoformat()
        )

        with self.lock:
            self.tasks[task_id] = task

        return task

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务"""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

    def list_tasks(self, limit: int = 50) -> List[TaskStatus]:
        """列出任务"""
        with self.lock:
            tasks = list(self.tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]

    def can_start_download(self) -> bool:
        """检查是否可以开始新下载"""
        with self.lock:
            return self.active_downloads < config.MAX_CONCURRENT_DOWNLOADS

    def increment_active(self):
        """增加活动下载数"""
        with self.lock:
            self.active_downloads += 1

    def decrement_active(self):
        """减少活动下载数"""
        with self.lock:
            self.active_downloads -= 1

task_manager = TaskManager()
```

**Step 3: 编写任务管理器测试**

```python
# tests/test_task_manager.py
import pytest
from backend.task_manager import TaskManager
from backend.models import PackageRequest

def test_create_task():
    """测试创建任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)

    assert task.task_id is not None
    assert task.status == "pending"

def test_get_task():
    """测试获取任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)
    retrieved = manager.get_task(task.task_id)

    assert retrieved is not None
    assert retrieved.task_id == task.task_id

def test_update_task():
    """测试更新任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)
    manager.update_task(task.task_id, status="running", progress=10)

    updated = manager.get_task(task.task_id)
    assert updated.status == "running"
    assert updated.progress == 10

def test_concurrent_limit():
    """测试并发限制"""
    manager = TaskManager()

    # 模拟已达到限制
    for _ in range(3):
        manager.increment_active()

    assert not manager.can_start_download()
```

**Step 4: 运行测试**

```bash
pytest tests/test_task_manager.py -v
```

**Step 5: 提交**

```bash
git add backend/models.py backend/task_manager.py tests/test_task_manager.py
git commit -m "feat: implement data models and task manager"
```

---

### Task 5.2: 创建 FastAPI 应用主文件

**Files:**
- Create: `backend/app.py`
- Create: `backend/main.py` (入口点)

**Step 1: 创建 FastAPI 应用**

```python
# backend/app.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

from backend.models import PackageRequest, TaskStatus
from backend.task_manager import task_manager
from backend.config import config

app = FastAPI(
    title="离线软件包下载服务",
    description="自动解析并下载 RPM/DEB 包及其依赖",
    version="2.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由
from backend import api_routes

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "active_downloads": task_manager.active_downloads,
        "total_tasks": len(task_manager.tasks)
    }

@app.get("/api/systems")
async def get_supported_systems():
    """获取支持的系统列表"""
    return config.DISTRIBUTIONS
```

**Step 2: 创建 API 路由**

```python
# backend/api_routes.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import tarfile
import threading

from backend.models import PackageRequest
from backend.task_manager import task_manager
from backend.config import config
from backend.resolvers.rpm import RPMRepodataParser, RPMDependencyResolver
from backend.resolvers.deb import DEBPackageParser, DEBDependencyResolver
from backend.downloaders.http import PackageDownloader

router = APIRouter(prefix="/api", tags=["api"])

def run_download_task(task_id: str, request: PackageRequest):
    """后台执行下载任务"""
    try:
        task = task_manager.get_task(task_id)
        task_manager.update_task(
            task_id,
            status="running",
            progress=10,
            message="正在解析依赖..."
        )
        task_manager.increment_active()

        # 解析依赖
        if request.system_type == "rpm":
            dist_config = config.DISTRIBUTIONS.get(request.distribution)
            if not dist_config:
                raise ValueError(f"不支持的发行版: {request.distribution}")

            parser = RPMRepodataParser(dist_config["baseos"])
            parser.load_metadata()
            parser.parse_packages()

            resolver = RPMDependencyResolver(parser)
            packages = []
            for pkg_name in request.packages:
                packages.extend(resolver.resolve(pkg_name))

            download_list = resolver.get_download_list(packages)

        else:  # deb
            dist_config = config.DISTRIBUTIONS.get(request.distribution)
            if not dist_config:
                raise ValueError(f"不支持的发行版: {request.distribution}")

            parser = DEBPackageParser(dist_config["main"])
            parser.load_packages()

            resolver = DEBDependencyResolver(parser)
            packages = []
            for pkg_name in request.packages:
                packages.extend(resolver.resolve(pkg_name))

            download_list = resolver.get_download_list(packages)

        task_manager.update_task(
            task_id,
            progress=30,
            message=f"找到 {len(download_list)} 个包,开始下载..."
        )

        # 下载
        output_dir = config.DOWNLOAD_DIR / task_id / "packages"
        downloader = PackageDownloader(max_workers=5)

        progress_count = [0]
        def progress_callback(current, total, pkg):
            progress_count[0] += 1
            progress = 30 + int((progress_count[0] / total) * 50)
            task_manager.update_task(
                task_id,
                progress=progress,
                message=f"正在下载: {pkg.get('name', pkg.get('Package'))} ({progress_count[0]}/{total})"
            )

        results = downloader.download_packages(
            download_list,
            output_dir,
            progress_callback
        )

        task_manager.update_task(
            task_id,
            progress=85,
            message="正在打包..."
        )

        # 打包
        tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(output_dir.parent, arcname="packages")

        task_manager.update_task(
            task_id,
            status="completed",
            progress=100,
            message="下载完成!",
            packages_count=len(download_list),
            total_size=f"{Path(tarball_path).stat().st_size / (1024*1024):.2f} MB",
            completed_at=datetime.now().isoformat(),
            download_url=f"/api/download/{task_id}"
        )

    except Exception as e:
        task_manager.update_task(
            task_id,
            status="failed",
            message=f"下载失败: {str(e)}",
            error=str(e)
        )
    finally:
        task_manager.decrement_active()

@router.post("/download")
async def create_download_task(
    request: PackageRequest,
    background_tasks: BackgroundTasks
):
    """创建下载任务"""
    task = task_manager.create_task(request)

    background_tasks.add_task(run_download_task, task.task_id, request)

    return {
        "task_id": task.task_id,
        "status": task.status,
        "message": "任务已创建,正在处理..."
    }

@router.get("/tasks")
async def list_tasks(limit: int = 50):
    """列出所有任务"""
    tasks = task_manager.list_tasks(limit)
    return {"tasks": [t.dict() for t in tasks]}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.dict()

@router.get("/download/{task_id}")
async def download_file(task_id: str):
    """下载生成的压缩包"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
    if not tarball_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=tarball_path,
        filename=f"packages-{task_id}.tar.gz",
        media_type="application/gzip"
    )

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务及文件"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除文件
    output_dir = config.DOWNLOAD_DIR / task_id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
    if tarball_path.exists():
        tarball_path.unlink()

    # 删除任务
    with task_manager.lock:
        del task_manager.tasks[task_id]

    return {"message": "任务已删除"}
```

**Step 3: 创建入口点**

```python
# backend/main.py
import uvicorn
from backend.app import app
from backend.config import config

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info"
    )
```

**Step 4: 提交**

```bash
git add backend/app.py backend/api_routes.py backend/main.py
git commit -m "feat: implement FastAPI application and API routes"
```

---

## Phase 6: 前端界面 (2 小时)

### Task 6.1: 创建 HTML 主页面

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/app.js`

**Step 1: 创建 HTML 结构**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>离线软件包下载工具</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🔧 离线软件包下载工具</h1>
            <nav>
                <button id="btn-tasks">任务历史</button>
                <button id="btn-settings">设置</button>
            </nav>
        </header>

        <main>
            <section class="card">
                <h2>创建下载任务</h2>

                <div class="form-group">
                    <label>1. 选择系统类型</label>
                    <select id="system-type">
                        <option value="rpm">RPM (CentOS/RHEL/Fedora)</option>
                        <option value="deb">DEB (Debian/Ubuntu)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>2. 选择发行版</label>
                    <select id="distribution">
                        <option value="centos-8">CentOS 8</option>
                        <option value="centos-7">CentOS 7</option>
                        <option value="ubuntu-22">Ubuntu 22.04 LTS</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>3. 选择架构</label>
                    <select id="arch">
                        <option value="auto">自动检测</option>
                        <option value="x86_64">x86_64</option>
                        <option value="aarch64">aarch64</option>
                    </select>
                </div>

                <div class="form-group">
                    <label>4. 输入包名</label>
                    <div id="package-tags" class="package-tags"></div>
                    <input type="text" id="package-input" placeholder="输入包名后按回车...">
                    <div class="form-actions">
                        <button id="btn-search">🔍 搜索包</button>
                        <button id="btn-template">📦 预设模板</button>
                    </div>
                </div>

                <div class="form-group">
                    <label>
                        <input type="checkbox" id="deep-download">
                        递归下载所有依赖
                    </label>
                </div>

                <button id="btn-download" class="btn-primary">🚀 开始下载</button>
            </section>

            <section class="card" id="progress-section" style="display: none;">
                <h2>📥 下载进度</h2>
                <div class="progress-container">
                    <div class="progress-bar" id="progress-bar">0%</div>
                </div>
                <p id="progress-message">正在准备...</p>
                <div class="log-container" id="log-container"></div>
            </section>

            <section class="card" id="tasks-section">
                <h2>最近任务</h2>
                <div id="task-list"></div>
            </section>
        </main>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>
```

**Step 2: 创建样式文件**

```css
/* frontend/css/style.css */
:root {
    --primary-color: #2563eb;
    --success-color: #10b981;
    --error-color: #ef4444;
    --bg-color: #f8fafc;
    --border-color: #e2e8f0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg-color);
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
}

header h1 {
    color: #1f2937;
}

nav button {
    padding: 8px 16px;
    margin-left: 10px;
    border: 1px solid var(--border-color);
    background: white;
    border-radius: 6px;
    cursor: pointer;
}

.card {
    background: white;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.form-group {
    margin-bottom: 20px;
}

label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
}

select, input {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 14px;
}

.package-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}

.tag {
    background: #dbeafe;
    padding: 4px 12px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.tag button {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 18px;
    color: #6b7280;
}

.form-actions {
    margin-top: 10px;
}

.form-actions button {
    padding: 8px 16px;
    margin-right: 10px;
    border: 1px solid var(--border-color);
    background: white;
    border-radius: 6px;
    cursor: pointer;
}

.btn-primary {
    width: 100%;
    padding: 12px;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
}

.btn-primary:hover {
    background: #1d4ed8;
}

.progress-container {
    background: #e5e7eb;
    height: 32px;
    border-radius: 16px;
    overflow: hidden;
    margin: 20px 0;
}

.progress-bar {
    background: var(--primary-color);
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 500;
    transition: width 0.3s ease;
}

.log-container {
    background: #1f2937;
    color: #f3f4f6;
    padding: 16px;
    border-radius: 8px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    max-height: 300px;
    overflow-y: auto;
    margin-top: 16px;
}

.log-entry {
    margin: 4px 0;
    padding-left: 12px;
    border-left: 2px solid #6b7280;
}

.task-item {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.task-item.completed {
    border-left: 4px solid var(--success-color);
}

.task-item.failed {
    border-left: 4px solid var(--error-color);
}

@media (max-width: 768px) {
    .container {
        padding: 12px;
    }
    .card {
        padding: 16px;
    }
}
```

**Step 3: 创建 JavaScript 主逻辑**

```javascript
// frontend/js/app.js

class PackageInput {
    constructor() {
        this.packages = [];
        this.container = document.getElementById('package-tags');
        this.input = document.getElementById('package-input');
        this.init();
    }

    init() {
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addPackage(this.input.value.trim());
                this.input.value = '';
            }
        });
        this.render();
    }

    addPackage(name) {
        if (name && !this.packages.includes(name)) {
            this.packages.push(name);
            this.render();
        }
    }

    removePackage(index) {
        this.packages.splice(index, 1);
        this.render();
    }

    render() {
        this.container.innerHTML = this.packages.map((pkg, i) => `
            <span class="tag">
                ${pkg}
                <button onclick="window.app.packageInput.removePackage(${i})">×</button>
            </span>
        `).join('');
    }

    getPackages() {
        return this.packages;
    }
}

class TaskList {
    constructor() {
        this.container = document.getElementById('task-list');
        this.load();
        setInterval(() => this.load(), 5000);
    }

    async load() {
        try {
            const response = await fetch('/api/tasks?limit=10');
            const data = await response.json();
            this.render(data.tasks);
        } catch (error) {
            console.error('Failed to load tasks:', error);
        }
    }

    render(tasks) {
        if (tasks.length === 0) {
            this.container.innerHTML = '<p style="color: #6b7280; text-align: center;">暂无任务</p>';
            return;
        }

        this.container.innerHTML = tasks.map(task => `
            <div class="task-item ${task.status}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${task.packages.join(', ')}</strong>
                        <div style="font-size: 13px; color: #6b7280; margin-top: 4px;">
                            ${task.system_type.toUpperCase()} - ${task.created_at}
                        </div>
                    </div>
                    <div>
                        ${this.getStatusBadge(task.status)}
                        ${task.status === 'completed' ? `
                            <button onclick="window.app.downloadFile('${task.task_id}')" style="margin-left: 10px; padding: 6px 12px;">
                                下载
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 14px;">${task.message}</div>
            </div>
        `).join('');
    }

    getStatusBadge(status) {
        const badges = {
            'pending': '<span style="background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-size: 12px;">⏳ 等待中</span>',
            'running': '<span style="background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; font-size: 12px;">🔄 进行中</span>',
            'completed': '<span style="background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-size: 12px;">✅ 已完成</span>',
            'failed': '<span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 12px;">❌ 失败</span>'
        };
        return badges[status] || '';
    }
}

class App {
    constructor() {
        this.packageInput = new PackageInput();
        this.taskList = new TaskList();
        this.initEventListeners();
    }

    initEventListeners() {
        document.getElementById('btn-download').addEventListener('click', () => this.startDownload());
        document.getElementById('system-type').addEventListener('change', () => this.updateDistributions());
    }

    async startDownload() {
        const packages = this.packageInput.getPackages();
        if (packages.length === 0) {
            alert('请输入至少一个包名');
            return;
        }

        const request = {
            packages: packages,
            system_type: document.getElementById('system-type').value,
            distribution: document.getElementById('distribution').value,
            arch: document.getElementById('arch').value,
            deep_download: document.getElementById('deep-download').checked
        };

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(request)
            });

            const result = await response.json();

            // 显示进度区域
            document.getElementById('progress-section').style.display = 'block';

            // 开始轮询进度
            this.pollProgress(result.task_id);

            // 刷新任务列表
            this.taskList.load();

        } catch (error) {
            alert('下载失败: ' + error.message);
        }
    }

    async pollProgress(taskId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${taskId}`);
                const task = await response.json();

                // 更新进度
                document.getElementById('progress-bar').style.width = `${task.progress}%`;
                document.getElementById('progress-bar').textContent = `${task.progress}%`;
                document.getElementById('progress-message').textContent = task.message;

                // 完成或失败时停止轮询
                if (task.status === 'completed') {
                    clearInterval(interval);
                    alert('下载完成!');
                    this.downloadFile(taskId);
                    this.taskList.load();
                } else if (task.status === 'failed') {
                    clearInterval(interval);
                    alert('下载失败: ' + task.error);
                    this.taskList.load();
                }

            } catch (error) {
                console.error('Failed to poll progress:', error);
            }
        }, 2000);
    }

    downloadFile(taskId) {
        window.location.href = `/api/download/${taskId}`;
    }

    updateDistributions() {
        // 根据系统类型更新发行版选项
        // 这里可以扩展为从 API 获取
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
```

**Step 4: 更新 FastAPI 应用以服务静态文件**

```python
# 添加到 backend/app.py

from fastapi.staticfiles import StaticFiles

# 挂载静态文件
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = Path("frontend/index.html")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
```

**Step 5: 提交**

```bash
git add frontend/
git commit -m "feat: implement frontend UI with vanilla JavaScript"
```

---

## Phase 7: Docker 部署 (30 分钟)

### Task 7.1: 创建 Docker 配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p downloads logs

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: 创建 docker-compose.yml**

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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 3: 创建 .dockerignore**

```bash
cat > .dockerignore << 'EOF
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.env
.git
.gitignore
*.md
docs/
tests/
.pytest_cache/
.coverage
htmlcov/
downloads/
logs/
*.tar.gz
*.rpm
*.deb
EOF
```

**Step 4: 构建和测试**

```bash
docker-compose build
docker-compose up -d
curl http://localhost:8000/api/health
```

**Step 5: 提交**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker deployment configuration"
```

---

## Phase 8: 文档和测试 (1 小时)

### Task 8.1: 创建 README 和文档

**Files:**
- Create: `README.md` (覆盖现有)
- Create: `DEPLOYMENT.md`
- Create: `API.md`

**Step 1: 创建主 README**

```markdown
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

## 许可证

MIT License
```

**Step 2: 创建部署文档**

```markdown
# 部署指南

## Docker 部署

```bash
docker-compose up -d
```

## Systemd 服务

创建 `/etc/systemd/system/package-downloader.service`:

```ini
[Unit]
Description=Offline Package Downloader
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/package-downloader
ExecStart=/usr/bin/python3 backend/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl enable package-downloader
sudo systemctl start package-downloader
```

## Nginx 反向代理

```nginx
server {
    listen 80;
    server_name packages.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```
```

**Step 3: 运行完整测试**

```bash
pytest tests/ -v --cov=backend
```

**Step 4: 提交**

```bash
git add *.md
git commit -m "docs: add comprehensive documentation"
```

---

## Phase 9: 优化和清理 (30 分钟)

### Task 9.1: 代码优化

**Files:**
- Modify: `backend/resolvers/rpm.py`
- Modify: `backend/resolvers/deb.py`
- Modify: `frontend/js/app.js`

**Step 1: 添加错误处理和日志**

```python
# 添加到所有主要模块
import logging
logger = logging.getLogger(__name__)
```

**Step 2: 添加输入验证**

```python
# 在 API 路由中添加更严格的验证
```

**Step 3: 运行代码格式化**

```bash
black backend/ tests/
flake8 backend/
mypy backend/
```

**Step 4: 最终测试**

```bash
pytest tests/ -v
```

**Step 5: 最终提交**

```bash
git add .
git commit -m "refactor: code optimization and error handling improvements"
```

---

## 完成!

实施计划已完成。你可以:

1. **查看完整计划**: `docs/plans/2024-02-06-offline-package-downloader.md`
2. **开始实施**: 选择下面的执行方式

### 执行选项

**选项 1: 子代理驱动 (当前会话)**
- 我将使用专门的子代理逐任务执行
- 每个任务后进行代码审查
- 快速迭代

**选项 2: 独立会话 (并行)**
- 在新会话中批量执行
- 使用检查点验证
- 适合长时间运行的任务

**选择哪个?**
