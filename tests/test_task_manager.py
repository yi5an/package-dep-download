import pytest
from backend.task_manager import TaskManager
from backend.models import PackageRequest

def test_create_task():
    """测试创建任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)

    assert task.task_id is not None
    assert task.status == "pending"

def test_get_task():
    """测试获取任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)
    retrieved = manager.get_task(task.task_id)

    assert retrieved is not None
    assert retrieved.task_id == task.task_id

def test_update_task():
    """测试更新任务"""
    manager = TaskManager()

    request = PackageRequest(
        packages=["nginx"],
        system_type="rpm",
        distribution="centos-8"
    )

    task = manager.create_task(request)
    manager.update_task(task.task_id, status="running", progress=10)

    updated = manager.get_task(task.task_id)
    assert updated.status == "running"
    assert updated.progress == 10

def test_concurrent_limit():
    """测试并发限制"""
    manager = TaskManager()

    # 模拟已达到限制
    for _ in range(3):
        manager.increment_active()

    assert not manager.can_start_download()
