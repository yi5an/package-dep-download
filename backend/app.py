from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.models import PackageRequest
from backend.task_manager import task_manager
from backend.config import config

app = FastAPI(
    title="离线软件包下载服务",
    description="自动解析并下载 RPM/DEB 包及其依赖",
    version="2.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "active_downloads": task_manager.active_downloads,
        "total_tasks": len(task_manager.tasks)
    }

@app.get("/api/systems")
async def get_supported_systems():
    """获取支持的系统列表"""
    return config.DISTRIBUTIONS

# 导入路由
from backend import api_routes
app.include_router(api_routes.router)

# 静态文件服务
@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面"""
    index_path = Path("frontend/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="前端文件未找到")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

app.mount("/static", StaticFiles(directory="frontend"), name="static")
