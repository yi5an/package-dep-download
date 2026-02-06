import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 服务配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 下载配置
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))

    # 存储路径
    BASE_DIR: Path = Path(__file__).parent.parent
    DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", BASE_DIR / "downloads"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))

    # 发行版配置
    DISTRIBUTIONS = {
        "centos-7": {
            "type": "rpm",
            "name": "CentOS 7",
            "baseos": "https://mirrors.aliyun.com/centos/7/os/x86_64/",
        },
        "centos-8": {
            "type": "rpm",
            "name": "CentOS 8",
            "baseos": "https://mirrors.aliyun.com/centos/8/BaseOS/x86_64/os/",
        },
        "ubuntu-22": {
            "type": "deb",
            "name": "Ubuntu 22.04",
            "main": "http://archive.ubuntu.com/ubuntu/dists/jammy/main/",
        },
    }

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
