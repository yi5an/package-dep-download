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
        base_url = self.mirror_url.split("/dists/")[0]
        return f"{base_url}/{filename}"


class DEBDependencyResolver:
    """DEB 依赖解析器"""

    def __init__(self, parser: DEBPackageParser):
        self.parser = parser
        self.resolved = set()

    def resolve(self, package_name: str) -> list:
        """递归解析包及其所有依赖"""
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
        """解析 Depends 字段"""
        if not depends_str:
            return []

        dependencies = []

        # 分割逗号分隔的依赖
        for part in depends_str.split(","):
            part = part.strip()

            # 移除版本限制
            match = re.match(r'^([a-zA-Z0-9+.-]+)', part)
            if match:
                dep_name = match.group(1)
                dependencies.append(dep_name)

        return dependencies

    def get_download_list(self, packages: list) -> list:
        """获取去重的下载列表"""
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
