# 测试策略

## 测试金字塔

```
        /\
       /  \        E2E 测试 (10%)
      /____\       - 完整下载流程测试
     /      \      - 用户界面测试
    /        \
   /          \    集成测试 (30%)
  /____________\   - API 端点测试
 /              \  - 依赖解析测试
/________________\
                 单元测试 (60%)
                 - 各组件功能测试
```

## 单元测试

### 依赖解析器测试

```python
# tests/test_rpm_resolver.py
import pytest
from backend.resolvers import RPMRepodataParser, RPMDependencyResolver

def test_load_metadata():
    """测试元数据加载"""
    parser = RPMRepodataParser("https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/")
    parser.load_metadata()
    assert len(parser.package_cache) > 0
    assert "bash" in parser.package_cache

def test_resolve_simple_package():
    """测试简单包解析"""
    parser = RPMRepodataParser("https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/")
    parser.load_metadata()

    resolver = RPMDependencyResolver(parser)
    packages = resolver.resolve("nginx")

    assert len(packages) > 0
    assert any(p["name"] == "nginx" for p in packages)

def test_resolve_with_dependencies():
    """测试带依赖的包解析"""
    parser = RPMRepodataParser("https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/")
    parser.load_metadata()

    resolver = RPMDependencyResolver(parser)
    packages = resolver.resolve("docker-ce")

    # docker-ce 应该有很多依赖
    assert len(packages) > 10

def test_circular_dependencies():
    """测试循环依赖处理"""
    # A -> B -> C -> A
    resolver = RPMDependencyResolver(mock_parser)
    # 应该能正确处理循环依赖
    packages = resolver.resolve("package-a")
    assert len(packages) > 0
```

### 下载器测试

```python
# tests/test_downloader.py
import pytest
from backend.downloaders import PackageDownloader
from pathlib import Path

def test_download_single_package(tmp_path):
    """测试单包下载"""
    downloader = PackageDownloader(max_workers=1)
    pkg = {
        "name": "test-package",
        "url": "http://example.com/test.rpm",
        "version": "1.0"
    }

    # Mock requests
    with mock.patch('requests.get') as mock_get:
        mock_get.return_value = MockResponse(content=b"test")

        result = downloader._download_single(pkg, tmp_path)

        assert result.exists()
        assert result.name == "test.rpm"

def test_download_with_resume(tmp_path):
    """测试断点续传"""
    # 创建部分下载的文件
    partial_file = tmp_path / "partial.rpm"
    partial_file.write_bytes(b"partial content")

    # 应该从断点继续
    # ...

def test_concurrent_downloads(tmp_path):
    """测试并发下载"""
    packages = [
        {"url": f"http://example.com/pkg{i}.rpm", "name": f"pkg{i}"}
        for i in range(10)
    ]

    downloader = PackageDownloader(max_workers=5)

    with mock.patch('requests.get'):
        results = downloader.download_packages(packages, tmp_path)

    assert len(results["success"]) == 10
    assert len(results["failed"]) == 0
```

### API 测试

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_create_download_task():
    """测试创建下载任务"""
    response = client.post("/api/download", json={
        "packages": ["nginx"],
        "system_type": "rpm",
        "distribution": "centos-8",
        "arch": "x86_64"
    })

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"

def test_get_task_status():
    """测试获取任务状态"""
    # 先创建任务
    create_response = client.post("/api/download", json={
        "packages": ["nginx"],
        "system_type": "rpm",
        "distribution": "centos-8"
    })
    task_id = create_response.json()["task_id"]

    # 获取状态
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id

def test_invalid_package_name():
    """测试无效包名"""
    response = client.post("/api/download", json={
        "packages": ["invalid-package-!@#"],
        "system_type": "rpm",
        "distribution": "centos-8"
    })

    assert response.status_code == 422  # Validation error

def test_search_packages():
    """测试包搜索"""
    response = client.get("/api/packages?type=rpm&dist=centos-8&q=nginx")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

## 集成测试

### 完整下载流程测试

```python
# tests/integration/test_full_download.py
import pytest
import time
from testclient import TestClient

def test_full_rpm_download():
    """测试完整的 RPM 下载流程"""
    client = TestClient()

    # 1. 创建任务
    response = client.post("/api/download", json={
        "packages": ["nano"],  # 小包,下载快
        "system_type": "rpm",
        "distribution": "centos-8"
    })
    task_id = response.json()["task_id"]

    # 2. 等待完成
    max_wait = 300  # 5分钟
    start = time.time()

    while time.time() - start < max_wait:
        response = client.get(f"/api/tasks/{task_id}")
        data = response.json()

        if data["status"] in ["completed", "failed"]:
            break

        time.sleep(5)

    # 3. 验证结果
    assert data["status"] == "completed"
    assert data["packages_count"] > 0

    # 4. 下载文件
    download_response = client.get(f"/api/download/{task_id}")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/gzip"

def test_sse_stream():
    """测试 SSE 实时推送"""
    import sseclient

    client = TestClient()
    response = client.post("/api/download", json={
        "packages": ["nano"],
        "system_type": "rpm",
        "distribution": "centos-8"
    })
    task_id = response.json()["task_id"]

    # 连接 SSE
    sse_response = client.get(f"/api/events/{task_id}", stream=True)
    client = sseclient.SSEClient(sse_response)

    events_received = []

    for event in client.events():
        data = json.loads(event.data)
        events_received.append(data)

        if event.event == "completed":
            break

    assert len(events_received) > 0
    assert any(e["status"] == "completed" for e in events_received)
```

## E2E 测试

### 使用 Playwright 进行 E2E 测试

```python
# tests/e2e/test_ui.py
from playwright.sync_api import Page, expect

def test_download_flow(page: Page):
    """测试完整的用户下载流程"""
    # 1. 打开页面
    page.goto("http://localhost:8000")

    # 2. 输入包名
    page.fill("#package-input", "nginx")
    page.press("#package-input", "Enter")

    # 3. 选择系统
    page.select_option("#system-type", "rpm")
    page.select_option("#distribution", "centos-8")

    # 4. 点击下载
    page.click("#start-download")

    # 5. 等待完成
    expect(page.locator(".progress-bar")).to_have_attribute("style", "width: 100%")

    # 6. 验证下载
    expect(page.locator(".download-button")).to_be_visible()

def test_package_search(page: Page):
    """测试包搜索功能"""
    page.goto("http://localhost:8000")

    # 触发搜索
    page.fill("#package-input", "ngin")
    page.wait_for_selector(".suggestion-item")

    # 验证结果
    suggestions = page.locator(".suggestion-item")
    expect(suggestions).to_have_count greater_than(0)
    expect(suggestions.first).to_contain_text("nginx")

def test_error_handling(page: Page):
    """测试错误处理"""
    page.goto("http://localhost:8000")

    # 输入无效包名
    page.fill("#package-input", "invalid-package-xxx")
    page.click("#start-download")

    # 验证错误提示
    expect(page.locator(".error-message")).to_be_visible()
    expect(page.locator(".error-message")).to_contain_text("不存在")
```

## 性能测试

### 压力测试

```python
# tests/performance/test_load.py
import asyncio
import aiohttp

async def create_task(session, package_name):
    async with session.post("http://localhost:8000/api/download", json={
        "packages": [package_name],
        "system_type": "rpm",
        "distribution": "centos-8"
    }) as response:
        return await response.json()

async def test_concurrent_requests():
    """测试并发请求"""
    async with aiohttp.ClientSession() as session:
        # 创建 10 个并发请求
        tasks = [
            create_task(session, f"package{i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # 验证都成功创建
        assert all("task_id" in r for r in results)

async def test_large_package_list():
    """测试大量包下载"""
    packages = [f"package{i}" for i in range(100)]

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/download", json={
            "packages": packages,
            "system_type": "rpm",
            "distribution": "centos-8"
        }) as response:
            assert response.status == 200
```

## 测试数据

### Mock 数据

```python
# tests/fixtures.py
@pytest.fixture
def mock_rpm_metadata():
    """Mock RPM 元数据"""
    return {
        "bash": {
            "version": "5.0.0",
            "arch": "x86_64",
            "url": "http://example.com/bash.rpm",
            "requires": ["glibc"]
        },
        "glibc": {
            "version": "2.28",
            "arch": "x86_64",
            "url": "http://example.com/glibc.rpm",
            "requires": []
        }
    }

@pytest.fixture
def mock_server():
    """Mock 镜像服务器"""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import threading

    server = HTTPServer(("localhost", 8888), SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    yield server

    server.shutdown()
```

## 测试运行

### pytest 配置

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行 E2E 测试
pytest tests/e2e/

# 生成覆盖率报告
pytest --cov=backend --cov-report=html

# 运行性能测试
pytest tests/performance/ --benchmark-only
```

## CI/CD 集成

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest --cov=backend

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 测试最佳实践

1. **独立性**: 每个测试应该独立运行,不依赖其他测试
2. **可重复性**: 测试结果应该可重复
3. **快速**: 单元测试应该快速运行
4. **清晰**: 测试名称应该清楚描述测试内容
5. **Mock 外部依赖**: 网络、文件系统等应该被 mock
6. **清理**: 测试后应该清理创建的资源

测试策略完成!所有设计文档已写完。准备好开始实现了吗?
