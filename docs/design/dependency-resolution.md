# 依赖解析与下载实现设计

## 核心架构

```
┌──────────────────────────────────────────────────────────┐
│                    包下载服务层                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  RPM 下载器  │  │ DEB 下载器   │  │  缓存管理    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│                   依赖解析引擎                             │
│  ┌────────────────────┐  ┌────────────────────┐          │
│  │ repodata 解析器     │  │ Packages 解析器     │          │
│  │ (RPM)              │  │ (DEB)              │          │
│  └────────────────────┘  └────────────────────┘          │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│                   HTTP 下载层                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │  - 多线程下载                                       │   │
│  │  - 断点续传                                         │   │
│  │  - 镜像站故障自动切换                               │   │
│  │  - 下载进度回调                                     │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## RPM 系统实现

### 1. 镜像站配置

```python
RPM_MIRRORS = {
    "centos-7": {
        "baseos": "https://mirrors.aliyun.com/centos/7/os/x86_64/",
        "updates": "https://mirrors.aliyun.com/centos/7/updates/x86_64/",
        "extras": "https://mirrors.aliyun.com/centos/7/extras/x86_64/",
    },
    "centos-8": {
        "baseos": "https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/",
        "appstream": "https://mirrors.aliyun.com/centos/8/AppStream/x86_64/os/",
    },
    "ubuntu24": {
        "main": "http://archive.ubuntu.com/ubuntu/dists/noble/main/",
        "universe": "http://archive.ubuntu.com/ubuntu/dists/noble/universe/",
    },
    # ... 更多发行版
}
```

### 2. repodata 解析

```python
class RPMRepodataParser:
    """解析 RPM repodata"""

    def __init__(self, mirror_url: str):
        self.mirror_url = mirror_url
        self.package_cache = {}

    def load_metadata(self):
        """加载 repomd.xml 并获取 primary.xml.gz"""
        repomd_url = urljoin(self.mirror_url, "repodata/repomd.xml")
        repomd = requests.get(repomd_url).content

        root = ET.fromstring(repomd)

        # 查找 primary 数据位置
        for data in root.findall(".//{http://linux.duke.edu/metadata/repo}data[@type='primary']"):
            location = data.find(".//{http://linux.duke.edu/metadata/repo}location")
            primary_path = location.get("href")
            self.primary_xml = self._download_and_decompress(
                urljoin(self.mirror_url, primary_path)
            )

    def parse_packages(self):
        """解析所有包信息"""
        root = ET.fromstring(self.primary_xml)

        for pkg in root.findall(".//{http://linux.duke.edu/metadata/common}package"):
            name = pkg.find(".//{http://linux.duke.edu/metadata/common}name").text
            version = pkg.find(".//{http://linux.duke.edu/metadata/common}version")
            arch = pkg.find(".//{http://linux.duke.edu/metadata/common}arch").text
            location = pkg.find(".//{http://linux.duke.edu/metadata/common}location")
            url = urljoin(self.mirror_url, location.get("href"))

            # 解析依赖
            requires = []
            for req in pkg.findall(".//{http://linux.duke.edu/metadata/common}rpm:entry", {"rpm": "http://linux.duke.edu/metadata/rpm"}):
                req_name = req.get("name")
                requires.append(req_name)

            self.package_cache[name] = {
                "version": version.get("ver"),
                "arch": arch,
                "url": url,
                "requires": requires
            }
```

### 3. 依赖解析算法

```python
class RPMDependencyResolver:
    """RPM 依赖解析器"""

    def __init__(self, parser: RPMRepodataParser):
        self.parser = parser
        self.resolved = set()
        self.to_resolve = set()

    def resolve(self, package_name: str) -> List[Dict]:
        """递归解析依赖"""
        if package_name in self.resolved:
            return []

        pkg = self.parser.package_cache.get(package_name)
        if not pkg:
            raise ValueError(f"包 {package_name} 不存在")

        packages = [pkg]
        self.resolved.add(package_name)

        # 递归解析依赖
        for req in pkg["requires"]:
            if req and not req.startswith("/") and req not in self.resolved:
                packages.extend(self.resolve(req))

        return packages
```

## DEB 系统实现

### 1. Packages 解析

```python
class DEBPackageParser:
    """解析 DEB Packages.gz"""

    def __init__(self, mirror_url: str):
        self.mirror_url = mirror_url
        self.package_cache = {}

    def load_packages(self):
        """下载并解析 Packages.gz"""
        packages_url = urljoin(self.mirror_url, "Packages.gz")
        compressed = requests.get(packages_url).content
        packages_text = gzip.decompress(compressed).decode()

        # 解析每个包
        current_package = {}
        for line in packages_text.split("\n"):
            if line == "":  # 空行表示包信息结束
                if current_package:
                    pkg_name = current_package["Package"]
                    self.package_cache[pkg_name] = current_package
                    current_package = {}
            elif line.startswith(" "):  # 续行
                if current_package:
                    last_key = list(current_package.keys())[-1]
                    current_package[last_key] += "\n" + line.strip()
            else:  # 新字段
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_package[key.strip()] = value.strip()
```

### 2. DEB 依赖解析

```python
class DEBDependencyResolver:
    """DEB 依赖解析器"""

    def __init__(self, parser: DEBPackageParser):
        self.parser = parser
        self.resolved = set()

    def resolve(self, package_name: str) -> List[Dict]:
        """递归解析依赖"""
        if package_name in self.resolved:
            return []

        pkg = self.parser.package_cache.get(package_name)
        if not pkg:
            raise ValueError(f"包 {package_name} 不存在")

        packages = [pkg]
        self.resolved.add(package_name)

        # 解析 Depends 字段
        depends_str = pkg.get("Depends", "")
        dependencies = self._parse_depends(depends_str)

        for dep in dependencies:
            if dep not in self.resolved:
                packages.extend(self.resolve(dep))

        return packages

    def _parse_depends(self, depends_str: str) -> List[str]:
        """解析 Depends 字段
        示例: "libc6 (>= 2.27), libssl1.1 (>= 1.1.1)"
        """
        dependencies = []

        for part in depends_str.split(","):
            part = part.strip()
            # 移除版本限制
            name = part.split("(")[0].strip()
            if name:
                dependencies.append(name)

        return dependencies
```

## HTTP 下载器

```python
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class PackageDownloader:
    """多线程下载器"""

    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.session = requests.Session()

    def download_packages(self, packages: List[Dict], output_dir: Path,
                         progress_callback=None):
        """批量下载包"""
        os.makedirs(output_dir, exist_ok=True)

        results = {"success": [], "failed": [], "total": len(packages)}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._download_single,
                    pkg,
                    output_dir,
                    progress_callback
                ): pkg for pkg in packages
            }

            for i, future in enumerate(as_completed(futures)):
                pkg = futures[future]
                try:
                    filepath = future.result()
                    results["success"].append(filepath)
                    if progress_callback:
                        progress_callback(i + 1, len(packages), pkg)
                except Exception as e:
                    results["failed"].append({"package": pkg, "error": str(e)})

        return results

    def _download_single(self, pkg: Dict, output_dir: Path,
                        progress_callback=None) -> Path:
        """下载单个包"""
        url = pkg["url"]
        filename = os.path.basename(url)
        filepath = output_dir / filename

        # 断点续传
        if filepath.exists():
            return filepath

        response = self.session.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        return filepath
```

## 镜像站管理器

```python
class MirrorManager:
    """镜像站管理"""

    MIRRORS = {
        "aliyun": "https://mirrors.aliyun.com",
        "tsinghua": "https://mirrors.tuna.tsinghua.edu.cn",
        "ustc": "https://mirrors.ustc.edu.cn",
    }

    def __init__(self, primary="aliyun"):
        self.primary = primary
        self.fallback = [m for m in self.MIRRORS if m != primary]

    def get_url(self, distribution: str, repo: str) -> str:
        """获取镜像 URL"""
        return f"{self.MIRRORS[self.primary]}/{distribution}/{repo}/"

    def try_fallback(self, url: str) -> Optional[str]:
        """尝试备用镜像"""
        for mirror in self.fallback:
            try:
                fallback_url = url.replace(
                    self.MIRRORS[self.primary],
                    self.MIRRORS[mirror]
                )
                response = requests.head(fallback_url, timeout=5)
                if response.ok:
                    return fallback_url
            except:
                continue
        return None
```

## 使用流程

```python
# 下载 nginx 及其依赖 (CentOS 8)
parser = RPMRepodataParser("https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/")
parser.load_metadata()

resolver = RPMDependencyResolver(parser)
packages = resolver.resolve("nginx")

downloader = PackageDownloader(max_workers=5)
results = downloader.download_packages(
    packages,
    Path("/tmp/packages"),
    progress_callback=lambda i, total, pkg: print(f"{i}/{total}: {pkg['name']}")
)
```

这部分设计是否清晰?我继续下一部分的设计吗?
