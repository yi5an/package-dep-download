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

                # requires 和 provides 在 format 元素内部
                format_elem = pkg.find("common:format", ns)

                # 解析依赖
                requires = []
                if format_elem is not None:
                    requires_elem = format_elem.find("rpm:requires", ns)
                    if requires_elem is not None:
                        for req in requires_elem.findall("rpm:entry", ns):
                            req_name = req.get("name")
                            if req_name and not req_name.startswith("rpmlib("):
                                requires.append(req_name)

                    # 解析 provides - 用于处理库文件依赖
                    provides = []
                    provides_elem = format_elem.find("rpm:provides", ns)
                    if provides_elem is not None:
                        for prov in provides_elem.findall("rpm:entry", ns):
                            prov_name = prov.get("name")
                            if prov_name:
                                provides.append(prov_name)
                else:
                    provides = []

                self.package_cache[name] = {
                    "name": name,
                    "version": version,
                    "arch": arch,
                    "url": url,
                    "requires": requires,
                    "provides": provides,
                }
            except Exception as e:
                # 跳过解析失败的包
                import logging
                logging.warning(f"Failed to parse package {name_elem.text if name_elem else 'unknown'}: {e}")
                continue

    def find_package(self, name: str):
        """查找特定包"""
        return self.package_cache.get(name)


class RPMDependencyResolver:
    """RPM 依赖解析器"""

    def __init__(self, parser: RPMRepodataParser):
        self.parser = parser
        self.resolved = set()
        # 构建 provides 映射: 库名 -> 包名
        self.provides_map = {}
        self._build_provides_map()

    def _build_provides_map(self):
        """构建库文件到包的映射"""
        for pkg_name, pkg_info in self.parser.package_cache.items():
            for prov in pkg_info.get("provides", []):
                # 只记录库文件 (包含 .so)
                if ".so" in prov:
                    self.provides_map[prov] = pkg_name

    def resolve(self, package_name: str) -> list:
        """
        递归解析包及其所有依赖

        返回: 包列表 (包含输入包和所有依赖)
        """
        import logging
        logger = logging.getLogger(__name__)

        if package_name in self.resolved:
            logger.debug(f"跳过已解析的包: {package_name}")
            return []

        pkg = self.parser.find_package(package_name)
        if not pkg:
            logger.debug(f"包不存在: {package_name}")
            raise ValueError(f"Package '{package_name}' not found")

        logger.info(f"解析包: {package_name}, 依赖数量: {len(pkg.get('requires', []))}")
        packages = [pkg]
        self.resolved.add(package_name)

        # 递归解析依赖
        for req in pkg.get("requires", []):
            if not req:
                continue

            # 跳过 rpmlib 依赖
            if req.startswith("rpmlib("):
                logger.debug(f"  跳过 rpmlib 依赖: {req}")
                continue

            # 跳过以 / 开头的文件路径依赖
            # 这些通常由基础包提供,不在仓库中
            if req.startswith("/"):
                logger.debug(f"  跳过文件路径依赖: {req}")
                continue

            logger.debug(f"  处理依赖: {req}")

            # 尝试解析依赖
            try:
                # 首先尝试直接解析为包名
                dep_packages = self.resolve(req)
                packages.extend(dep_packages)
                logger.debug(f"    ✓ 找到包: {req}")
            except ValueError:
                # 如果找不到包,尝试作为库文件查找
                # 提取库名 (例如: libgpm.so.2()(64bit) -> libgpm.so.2)
                lib_name = self._extract_lib_name(req)
                if lib_name:
                    logger.debug(f"    作为库文件查找: {req} -> {lib_name}")
                    if lib_name in self.provides_map:
                        # 找到提供这个库的包
                        provider_pkg = self.provides_map[lib_name]
                        logger.debug(f"    ✓ 库由以下包提供: {provider_pkg}")
                        try:
                            dep_packages = self.resolve(provider_pkg)
                            packages.extend(dep_packages)
                        except ValueError:
                            logger.warning(f"    ✗ 提供者包不存在: {provider_pkg}")
                            continue
                    else:
                        logger.debug(f"    ✗ 库不在 provides_map 中: {lib_name}")
                        # 尝试直接查找 (可能库名稍有不同)
                        if lib_name.split('.')[0] in self.provides_map:
                            provider_pkg = self.provides_map[lib_name.split('.')[0]]
                            logger.debug(f"    ✓ 使用简化库名找到: {provider_pkg}")
                            try:
                                dep_packages = self.resolve(provider_pkg)
                                packages.extend(dep_packages)
                            except ValueError:
                                continue
                else:
                    logger.debug(f"    ✗ 找不到对应的包或库: {req}")
                    # 找不到对应的包,跳过
                    continue

        return packages

    def _extract_lib_name(self, req: str) -> str:
        """
        从依赖字符串中提取库名

        例如:
        - "libgpm.so.2()(64bit)" -> "libgpm.so.2()(64bit)"
        - "libperl.so()(64bit)" -> "libperl.so()(64bit)"
        - "libc.so.6(GLIBC_2.2.5)(64bit)" -> "libc.so.6()(64bit)"
        """
        import re
        # 匹配库文件名，包括架构标记
        # 例如: libgpm.so.2()(64bit) 或 libperl.so()(64bit)
        match = re.match(r'([a-z0-9._+-]+\.so[\d.]*\(?\)?(\([A-Z0-9_]+\))?\(\d+bit\))', req)
        if match:
            return match.group(1)

        # 如果上面不匹配，尝试简化版本：库名 + ()(64bit)
        match = re.match(r'([a-z0-9._+-]+\.so[\d.]*)\(\)\(64bit\)', req)
        if match:
            base_name = match.group(1)
            return f"{base_name}()(64bit)"

        # 最后尝试：提取库名.so.版本
        match = re.match(r'([a-z0-9._+-]+\.so[\d.]*)', req)
        if match:
            return match.group(1)

        return None

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
