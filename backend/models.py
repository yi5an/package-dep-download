from pydantic import BaseModel, Field
from typing import List, Optional


class PackageRequest(BaseModel):
    """包下载请求"""

    packages: List[str] = Field(..., min_length=1, max_length=100, description="包名列表")
    system_type: str = Field(..., pattern="^(rpm|deb)$", description="系统类型")
    distribution: str = Field(..., min_length=1, description="发行版")
    arch: str = Field(default="auto", description="架构")
    deep_download: bool = Field(default=False, description="是否递归下载")


class TaskStatus(BaseModel):
    """任务状态"""

    task_id: str
    status: str  # pending, running, completed, failed
    progress: int = Field(default=0, ge=0, le=100)
    message: str
    packages: Optional[List[str]] = None  # 添加包列表字段
    packages_count: int = 0
    total_size: str = "0 MB"
    system_type: Optional[str] = None  # 添加系统类型
    distribution: Optional[str] = None  # 添加发行版
    arch: Optional[str] = None  # 添加架构
    current_step: Optional[str] = None  # 添加当前步骤
    created_at: str
    completed_at: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None
