import uuid
import threading
from datetime import datetime
from typing import Dict, Optional

from backend.models import TaskStatus, PackageRequest
from backend.config import config


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, TaskStatus] = {}
        self.lock = threading.Lock()
        self.active_downloads = 0

    def create_task(self, request: PackageRequest) -> TaskStatus:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]

        task = TaskStatus(
            task_id=task_id,
            status="pending",
            progress=0,
            message="任务已创建",
            created_at=datetime.now().isoformat(),
        )

        with self.lock:
            self.tasks[task_id] = task

        return task

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
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

    def list_tasks(self, limit: int = 50) -> list:
        """列出任务"""
        with self.lock:
            tasks = list(self.tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]

    def can_start_download(self) -> bool:
        """检查是否可以开始新下载"""
        with self.lock:
            return self.active_downloads < config.MAX_CONCURRENT_DOWNLOADS

    def increment_active(self):
        """增加活动下载数"""
        with self.lock:
            self.active_downloads += 1

    def decrement_active(self):
        """减少活动下载数"""
        with self.lock:
            self.active_downloads -= 1


task_manager = TaskManager()
