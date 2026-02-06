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
