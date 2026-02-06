# API 接口设计

## REST API 端点

### 1. 创建下载任务

**POST** `/api/download`

**请求体**:
```json
{
    "packages": ["nginx", "python3"],
    "system_type": "rpm",
    "distribution": "centos-8",
    "arch": "x86_64",
    "deep_download": true
}
```

**响应**:
```json
{
    "task_id": "a1b2c3d4",
    "status": "pending",
    "message": "任务已创建,正在处理...",
    "estimated_time": 120
}
```

### 2. 获取任务状态

**GET** `/api/tasks/{task_id}`

**响应**:
```json
{
    "task_id": "a1b2c3d4",
    "status": "running",
    "progress": 45,
    "message": "正在下载依赖包...",
    "packages_count": 12,
    "total_size": "125.5 MB",
    "downloaded_size": "56.3 MB",
    "current_package": "openssl-libs-1.1.1k",
    "created_at": "2024-02-06T15:30:00",
    "completed_at": null
}
```

### 3. 列出所有任务

**GET** `/api/tasks?limit=20&offset=0`

**响应**:
```json
{
    "total": 45,
    "tasks": [
        {
            "task_id": "a1b2c3d4",
            "packages": ["nginx"],
            "system_type": "rpm",
            "distribution": "centos-8",
            "status": "completed",
            "progress": 100,
            "created_at": "2024-02-06T15:30:00",
            "download_url": "/api/download/a1b2c3d4"
        }
    ]
}
```

### 4. 下载文件

**GET** `/api/download/{task_id}`

返回生成的 tar.gz 文件

### 5. 删除任务

**DELETE** `/api/tasks/{task_id}`

**响应**:
```json
{
    "message": "任务已删除"
}
```

### 6. 搜索软件包

**GET** `/api/packages?type=rpm&dist=centos-8&q=nginx`

**响应**:
```json
{
    "results": [
        {
            "name": "nginx",
            "version": "1.20.1",
            "summary": "A high performance web server",
            "description": "Nginx is a web server...",
            "size": "1.2 MB",
            "license": "BSD"
        }
    ]
}
```

### 7. 获取支持的系统

**GET** `/api/systems`

**响应**:
```json
{
    "rpm": [
        {
            "id": "centos-8",
            "name": "CentOS 8",
            "arch": ["x86_64", "aarch64"]
        }
    ],
    "deb": [
        {
            "id": "ubuntu-22",
            "name": "Ubuntu 22.04 LTS",
            "arch": ["amd64", "arm64"]
        }
    ]
}
```

## Server-Sent Events 端点

### 实时进度推送

**GET** `/api/events/{task_id}`

**事件类型**:

1. **进度更新**:
```
event: progress
data: {"progress": 50, "message": "正在下载...", "current": "openssl-libs"}
```

2. **包下载完成**:
```
event: package_downloaded
data: {"package": "nginx-1.20.1", "size": "1.2 MB", "speed": "5.2 MB/s"}
```

3. **任务完成**:
```
event: completed
data: {
    "task_id": "a1b2c3d4",
    "download_url": "/api/download/a1b2c3d4",
    "packages_count": 12,
    "total_size": "125.5 MB"
}
```

4. **任务失败**:
```
event: error
data: {"error": "下载失败: 网络错误", "code": "NETWORK_ERROR"}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| INVALID_REQUEST | 请求参数无效 |
| PACKAGE_NOT_FOUND | 软件包不存在 |
| DEPENDENCY_ERROR | 依赖解析失败 |
| DOWNLOAD_ERROR | 下载失败 |
| NETWORK_ERROR | 网络错误 |
| STORAGE_ERROR | 存储空间不足 |
| TASK_LIMIT_EXCEEDED | 超过并发限制 |

## 错误响应格式

```json
{
    "error": {
        "code": "PACKAGE_NOT_FOUND",
        "message": "包 'invalid-package' 在 CentOS 8 仓库中不存在",
        "details": {
            "suggestions": ["nginx", "apache"]
        }
    }
}
```

## 请求/响应示例

### 完整下载流程

```javascript
// 1. 创建任务
const response = await fetch('/api/download', {
    method: 'POST',
    body: JSON.stringify({
        packages: ['nginx'],
        system_type: 'rpm',
        distribution: 'centos-8',
        arch: 'x86_64',
        deep_download: true
    })
});
const {task_id} = await response.json();

// 2. 监听进度
const eventSource = new EventSource(`/api/events/${task_id}`);
eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    updateProgress(data.progress);
    updateMessage(data.message);
});

eventSource.addEventListener('completed', (e) => {
    const data = JSON.parse(e.data);
    // 自动下载
    window.location.href = data.download_url;
    eventSource.close();
});

// 3. 下载完成后自动关闭连接
```

## 限流和安全

### 限流策略

- 同一 IP: 每分钟最多 10 个下载任务
- 全局: 最多 3 个并发下载任务
- 单次任务: 最多 100 个软件包

### 认证 (可选)

如果需要添加认证:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(token: str = Security(security)):
    if token.credentials != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=403, detail="Invalid token")
    return token.credentials

@app.post("/api/download", dependencies=[Depends(verify_token)])
async def create_download_task(...):
    ...
```

## 数据验证

使用 Pydantic 进行请求验证:

```python
from pydantic import BaseModel, Field, validator

class PackageRequest(BaseModel):
    packages: List[str] = Field(..., min_items=1, max_items=100)
    system_type: str = Field(..., regex="^(rpm|deb)$")
    distribution: str = Field(..., min_length=1)
    arch: str = Field(default="auto")
    deep_download: bool = Field(default=False)

    @validator('packages')
    def validate_packages(cls, v):
        for pkg in v:
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._+-]*$', pkg):
                raise ValueError(f'Invalid package name: {pkg}')
        return v

    @validator('arch')
    def validate_arch(cls, v):
        if v != 'auto' and v not in ['x86_64', 'aarch64', 'amd64', 'arm64']:
            raise ValueError('Invalid architecture')
        return v
```

API 设计完成,是否继续?
