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
