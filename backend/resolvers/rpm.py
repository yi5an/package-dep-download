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
