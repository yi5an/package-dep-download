#!/usr/bin/env python3
"""
离线软件包依赖下载服务 - 后端 API
支持通过 Web 界面下载 RPM/DEB 包及其依赖
"""

import os
import sys
import json
import uuid
import shutil
import subprocess
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse


# ==================== 配置 ====================
CONFIG = {
    "DOWNLOAD_DIR": Path("./downloads"),
    "MAX_FILE_AGE_HOURS": 24,  # 24小时后自动清理
    "MAX_CONCURRENT_DOWNLOADS": 3,
    "ALLOWED_ORIGINS": ["*"],  # 生产环境应该限制具体域名
}

# ==================== 数据模型 ====================
class PackageRequest(BaseModel):
    """包下载请求"""
    packages: List[str] = Field(..., description="包名列表", min_items=1)
    system_type: str = Field(..., description="系统类型: rpm/deb")
    distribution: str = Field(..., description="发行版: centos7, centos8, ubuntu20, etc.")
    deep_download: bool = Field(False, description="是否递归下载所有依赖")
    arch: str = Field("auto", description="架构: x86_64, aarch64, auto")


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    message: str
    packages_count: int = 0
    total_size: str = "0 MB"
    created_at: str
    completed_at: Optional[str] = None
    download_url: Optional[str] = None


# ==================== 任务管理 ====================
@dataclass
class DownloadTask:
    """下载任务"""
    task_id: str
    request: PackageRequest
    status: str = "pending"
    progress: int = 0
    message: str = "任务已创建"
    packages_count: int = 0
    total_size: str = "0 MB"
    created_at: str = ""
    completed_at: Optional[str] = None
    output_dir: Optional[Path] = None
    error: Optional[str] = None


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, DownloadTask] = {}
        self.lock = threading.Lock()
        self.active_downloads = 0

    def create_task(self, request: PackageRequest) -> DownloadTask:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        task = DownloadTask(
            task_id=task_id,
            request=request,
            created_at=datetime.now().isoformat(),
        )
        with self.lock:
            self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        with self.lock:
            return [asdict(task) for task in self.tasks.values()]

    def can_start_download(self) -> bool:
        """检查是否可以开始新下载"""
        with self.lock:
            return self.active_downloads < CONFIG["MAX_CONCURRENT_DOWNLOADS"]

    def increment_active(self):
        """增加活动下载数"""
        with self.lock:
            self.active_downloads += 1

    def decrement_active(self):
        """减少活动下载数"""
        with self.lock:
            self.active_downloads -= 1


task_manager = TaskManager()


# ==================== 包下载器 ====================
class PackageDownloader:
    """包下载器"""

    def __init__(self, task: DownloadTask):
        self.task = task
        self.output_dir = CONFIG["DOWNLOAD_DIR"] / task.task_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        task.output_dir = self.output_dir

    def download(self):
        """执行下载"""
        try:
            self.task_manager = task_manager
            task_manager.update_task(
                self.task.task_id,
                status="running",
                progress=10,
                message="开始下载..."
            )
            self.task_manager.increment_active()

            if self.task.request.system_type == "rpm":
                self._download_rpm()
            else:
                self._download_deb()

            # 打包
            task_manager.update_task(
                self.task.task_id,
                progress=80,
                message="正在打包..."
            )
            tarball_path = self._create_tarball()

            # 统计信息
            stats = self._get_stats()

            task_manager.update_task(
                self.task.task_id,
                status="completed",
                progress=100,
                message="下载完成!",
                packages_count=stats["count"],
                total_size=stats["size"],
                completed_at=datetime.now().isoformat(),
                download_url=f"/api/download/{self.task.task_id}"
            )

        except Exception as e:
            task_manager.update_task(
                self.task.task_id,
                status="failed",
                message=f"下载失败: {str(e)}",
                completed_at=datetime.now().isoformat()
            )
        finally:
            task_manager.decrement_active()

    def _download_rpm(self):
        """下载 RPM 包"""
        packages = " ".join(self.task.request.packages)
        deep = "--deep" if self.task.request.deep_download else ""

        script_path = Path(__file__).parent.parent / "offline-installer.sh"

        cmd = [
            str(script_path),
            "-t", "rpm",
            "-o", str(self.output_dir / "packages"),
            deep,
            packages
        ]

        task_manager.update_task(
            self.task.task_id,
            progress=20,
            message="正在分析 RPM 包依赖..."
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )

        if result.returncode != 0:
            raise Exception(f"RPM 下载失败: {result.stderr}")

        task_manager.update_task(
            self.task.task_id,
            progress=60,
            message="RPM 包下载完成"
        )

    def _download_deb(self):
        """下载 DEB 包"""
        packages = " ".join(self.task.request.packages)
        deep = "--deep" if self.task.request.deep_download else ""

        script_path = Path(__file__).parent.parent / "offline-installer.sh"

        cmd = [
            str(script_path),
            "-t", "deb",
            "-o", str(self.output_dir / "packages"),
            deep,
            packages
        ]

        task_manager.update_task(
            self.task.task_id,
            progress=20,
            message="正在分析 DEB 包依赖..."
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600
        )

        if result.returncode != 0:
            raise Exception(f"DEB 下载失败: {result.stderr}")

        task_manager.update_task(
            self.task.task_id,
            progress=60,
            message="DEB 包下载完成"
        )

    def _create_tarball(self) -> Path:
        """创建压缩包"""
        tarball_name = f"packages-{self.task.task_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.tar.gz"
        tarball_path = CONFIG["DOWNLOAD_DIR"] / tarball_name

        task_manager.update_task(
            self.task.task_id,
            progress=85,
            message="正在创建压缩包..."
        )

        subprocess.run(
            ["tar", "-czf", str(tarball_path), "-C", str(self.output_dir), "packages"],
            check=True
        )

        return tarball_path

    def _get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        packages_dir = self.output_dir / "packages"

        if self.task.request.system_type == "rpm":
            files = list(packages_dir.glob("*.rpm"))
        else:
            files = list(packages_dir.glob("*.deb"))

        total_size = sum(f.stat().st_size for f in files) if files else 0
        size_mb = f"{total_size / (1024*1024):.2f} MB"

        return {
            "count": len(files),
            "size": size_mb
        }


def run_download_task(task: DownloadTask):
    """在后台运行下载任务"""
    downloader = PackageDownloader(task)
    downloader.download()


# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="离线软件包依赖下载服务",
    description="通过 Web 界面下载 RPM/DEB 包及其所有依赖",
    version="2.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["ALLOWED_ORIGINS"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API 路由 ====================
@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>前端文件未找到</h1>")


@app.post("/api/download")
async def create_download_task(request: PackageRequest, background_tasks: BackgroundTasks):
    """创建下载任务"""
    # 验证输入
    if request.system_type not in ["rpm", "deb"]:
        raise HTTPException(status_code=400, detail="不支持的系统类型")

    # 创建任务
    task = task_manager.create_task(request)

    # 添加到后台任务
    background_tasks.add_task(run_download_task, task)

    return {
        "task_id": task.task_id,
        "status": task.status,
        "message": "任务已创建,正在处理..."
    }


@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务"""
    tasks = task_manager.list_tasks()
    # 按创建时间倒序排列
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return {"tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return asdict(task)


@app.get("/api/download/{task_id}")
async def download_file(task_id: str):
    """下载生成的压缩包"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    # 查找压缩包
    tarballs = list(CONFIG["DOWNLOAD_DIR"].glob(f"packages-{task_id}-*.tar.gz"))
    if not tarballs:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    tarball_path = tarballs[0]

    return FileResponse(
        path=tarball_path,
        filename=tarball_path.name,
        media_type="application/gzip"
    )


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务及文件"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除文件
    if task.output_dir and task.output_dir.exists():
        shutil.rmtree(task.output_dir)

    # 删除压缩包
    tarballs = list(CONFIG["DOWNLOAD_DIR"].glob(f"packages-{task_id}-*.tar.gz"))
    for tarball in tarballs:
        tarball.unlink()

    # 删除任务
    with task_manager.lock:
        del task_manager.tasks[task_id]

    return {"message": "任务已删除"}


@app.get("/api/systems")
async def get_supported_systems():
    """获取支持的系统列表"""
    return {
        "rpm": [
            {"id": "centos7", "name": "CentOS 7", "arch": ["x86_64", "aarch64"]},
            {"id": "centos8", "name": "CentOS 8 / Stream", "arch": ["x86_64", "aarch64"]},
            {"id": "rhel7", "name": "RHEL 7", "arch": ["x86_64", "aarch64"]},
            {"id": "rhel8", "name": "RHEL 8", "arch": ["x86_64", "aarch64"]},
            {"id": "rhel9", "name": "RHEL 9", "arch": ["x86_64", "aarch64"]},
            {"id": "fedora", "name": "Fedora", "arch": ["x86_64", "aarch64"]},
        ],
        "deb": [
            {"id": "ubuntu18", "name": "Ubuntu 18.04 LTS", "arch": ["amd64", "arm64"]},
            {"id": "ubuntu20", "name": "Ubuntu 20.04 LTS", "arch": ["amd64", "arm64"]},
            {"id": "ubuntu22", "name": "Ubuntu 22.04 LTS", "arch": ["amd64", "arm64"]},
            {"id": "ubuntu24", "name": "Ubuntu 24.04 LTS", "arch": ["amd64", "arm64"]},
            {"id": "debian10", "name": "Debian 10", "arch": ["amd64", "arm64"]},
            {"id": "debian11", "name": "Debian 11", "arch": ["amd64", "arm64"]},
            {"id": "debian12", "name": "Debian 12", "arch": ["amd64", "arm64"]},
        ]
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "active_downloads": task_manager.active_downloads,
        "total_tasks": len(task_manager.tasks)
    }


# ==================== 启动 ====================
if __name__ == "__main__":
    import uvicorn

    # 创建下载目录
    CONFIG["DOWNLOAD_DIR"].mkdir(parents=True, exist_ok=True)

    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
