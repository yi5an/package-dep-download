import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import requests
import gzip


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
            "rpm": "http://linux.duke.edu/metadata/rpm",
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
                version = (
                    version_elem.get("ver") if version_elem is not None else "unknown"
                )

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
                    "requires": requires,
                }
            except Exception:
                # 跳过解析失败的包
                continue

    def find_package(self, name: str):
        """查找特定包"""
        return self.package_cache.get(name)


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

        返回: 去重后的包列表
        """
        seen = set()
        download_list = []

        for pkg in packages:
            url = pkg.get("url")
            if url and url not in seen:
                seen.add(url)
                download_list.append(pkg)

        return download_list
