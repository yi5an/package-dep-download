from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import tarfile
from datetime import datetime

from backend.models import PackageRequest
from backend.task_manager import task_manager
from backend.config import config
from backend.resolvers.rpm import RPMRepodataParser, RPMDependencyResolver
from backend.resolvers.deb import DEBPackageParser, DEBDependencyResolver
from backend.downloaders.http import PackageDownloader

router = APIRouter(prefix="/api", tags=["api"])


def run_download_task(task_id: str, request: PackageRequest):
    """后台执行下载任务"""
    try:
        task_manager.update_task(
            task_id, status="running", progress=10, message="正在解析依赖..."
        )
        task_manager.increment_active()

        # 解析依赖
        if request.system_type == "rpm":
            dist_config = config.DISTRIBUTIONS.get(request.distribution)
            if not dist_config:
                raise ValueError(f"不支持的发行版: {request.distribution}")

            parser = RPMRepodataParser(dist_config["baseos"])
            parser.load_metadata()
            parser.parse_packages()

            resolver = RPMDependencyResolver(parser)
            packages = []
            for pkg_name in request.packages:
                packages.extend(resolver.resolve(pkg_name))

            download_list = resolver.get_download_list(packages)

        else:  # deb
            dist_config = config.DISTRIBUTIONS.get(request.distribution)
            if not dist_config:
                raise ValueError(f"不支持的发行版: {request.distribution}")

            # 映射架构: x86_64 -> amd64, aarch64 -> arm64
            arch_mapping = {
                "x86_64": "amd64",
                "aarch64": "arm64",
                "noarch": "all"
            }
            deb_arch = arch_mapping.get(request.arch, dist_config.get("arch", "amd64"))

            parser = DEBPackageParser(dist_config["main"], arch=deb_arch)
            parser.load_packages()

            resolver = DEBDependencyResolver(parser)
            packages = []
            for pkg_name in request.packages:
                packages.extend(resolver.resolve(pkg_name))

            download_list = resolver.get_download_list(packages)

        task_manager.update_task(
            task_id, progress=30, message=f"找到 {len(download_list)} 个包,开始下载..."
        )

        # 下载
        output_dir = config.DOWNLOAD_DIR / task_id / "packages"
        downloader = PackageDownloader(max_workers=5)

        progress_count = [0]

        def progress_callback(current, total, pkg):
            progress_count[0] += 1
            progress = 30 + int((progress_count[0] / total) * 50)
            task_manager.update_task(
                task_id,
                progress=progress,
                message=f"正在下载: {pkg.get('name', pkg.get('Package'))} "
                f"({progress_count[0]}/{total})",
            )

        downloader.download_packages(download_list, output_dir, progress_callback)

        task_manager.update_task(task_id, progress=85, message="正在打包...")

        # 打包
        tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(output_dir.parent, arcname="packages")

        task_manager.update_task(
            task_id,
            status="completed",
            progress=100,
            message="下载完成!",
            packages_count=len(download_list),
            total_size=f"{Path(tarball_path).stat().st_size / (1024*1024):.2f} MB",
            completed_at=datetime.now().isoformat(),
            download_url=f"/api/download/{task_id}",
        )

    except Exception as e:
        task_manager.update_task(
            task_id, status="failed", message=f"下载失败: {str(e)}", error=str(e)
        )
    finally:
        task_manager.decrement_active()


@router.post("/download")
async def create_download_task(
    request: PackageRequest, background_tasks: BackgroundTasks
):
    """创建下载任务"""
    task = task_manager.create_task(request)

    background_tasks.add_task(run_download_task, task.task_id, request)

    return {"task_id": task.task_id, "status": task.status, "message": "任务已创建,正在处理..."}


@router.get("/tasks")
async def list_tasks(limit: int = 50):
    """列出所有任务"""
    tasks = task_manager.list_tasks(limit)
    return {"tasks": [t.dict() for t in tasks]}


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.dict()


@router.get("/download/{task_id}")
async def download_file(task_id: str):
    """下载生成的压缩包"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
    if not tarball_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=tarball_path,
        filename=f"packages-{task_id}.tar.gz",
        media_type="application/gzip",
    )


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务及文件"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除文件
    output_dir = config.DOWNLOAD_DIR / task_id
    if output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)

    tarball_path = config.DOWNLOAD_DIR / f"packages-{task_id}.tar.gz"
    if tarball_path.exists():
        tarball_path.unlink()

    # 删除任务
    with task_manager.lock:
        del task_manager.tasks[task_id]

    return {"message": "任务已删除"}
