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
        "version": "1.0",
    }

    # Mock HTTP 响应
    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content = lambda chunk_size: [b"test content"]
    mock_response.status_code = 200

    with patch("requests.Session.get", return_value=mock_response):
        result = downloader._download_single(pkg, tmp_path)

    assert result.exists()
    assert result.name == "test.rpm"


def test_download_multiple_packages(tmp_path):
    """测试批量下载"""
    downloader = PackageDownloader(max_workers=2)

    packages = [
        {"name": "pkg1", "url": "http://example.com/pkg1.rpm"},
        {"name": "pkg2", "url": "http://example.com/pkg2.rpm"},
    ]

    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content = lambda chunk_size: [b"content"]
    mock_response.status_code = 200

    with patch("requests.Session.get", return_value=mock_response):
        results = downloader.download_packages(packages, tmp_path)

    assert results["total"] == 2
    assert len(results["success"]) == 2
    assert len(results["failed"]) == 0


def test_download_with_progress_callback(tmp_path):
    """测试带进度回调的下载"""
    downloader = PackageDownloader(max_workers=2)

    packages = [
        {"name": "pkg1", "url": "http://example.com/pkg1.rpm"},
        {"name": "pkg2", "url": "http://example.com/pkg2.rpm"},
    ]

    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content = lambda chunk_size: [b"content"]
    mock_response.status_code = 200

    progress_updates = []

    def mock_callback(current, total, pkg):
        progress_updates.append((current, total, pkg["name"]))

    with patch("requests.Session.get", return_value=mock_response):
        results = downloader.download_packages(packages, tmp_path, mock_callback)

    assert len(progress_updates) == 2
    assert results["total"] == 2
    assert len(results["success"]) == 2


def test_download_with_error(tmp_path):
    """测试下载失败处理"""
    downloader = PackageDownloader(max_workers=2)

    packages = [
        {"name": "pkg1", "url": "http://example.com/pkg1.rpm"},
        {"name": "pkg2", "url": "http://example.com/pkg2.rpm"},
    ]

    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content = lambda chunk_size: [b"content"]
    mock_response.status_code = 200

    def side_effect(*args, **kwargs):
        if "pkg2" in args[0]:
            raise Exception("Network error")
        return mock_response

    with patch("requests.Session.get", side_effect=side_effect):
        results = downloader.download_packages(packages, tmp_path)

    assert results["total"] == 2
    assert len(results["success"]) == 1
    assert len(results["failed"]) == 1
    assert "Network error" in results["failed"][0]["error"]


def test_download_package_without_url(tmp_path):
    """测试没有 URL 的包"""
    downloader = PackageDownloader(max_workers=1)

    pkg = {"name": "test-package"}

    with pytest.raises(ValueError, match="has no URL"):
        downloader._download_single(pkg, tmp_path)
