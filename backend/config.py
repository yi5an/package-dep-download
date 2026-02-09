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
        # RPM 发行版
        "centos-7": {
            "type": "rpm",
            "name": "CentOS 7",
            "baseos": "https://mirrors.aliyun.com/centos/7/os/x86_64/",
            "arch": "x86_64",
        },
        "centos-8": {
            "type": "rpm",
            "name": "CentOS 8 Stream",
            "baseos": "https://mirrors.aliyun.com/centos/8-stream/BaseOS/x86_64/os/",
            "arch": "x86_64",
        },
        "rhel-7": {
            "type": "rpm",
            "name": "RHEL 7",
            "baseos": "https://mirrors.aliyun.com/centos/7/os/x86_64/",
            "arch": "x86_64",
        },
        "rhel-8": {
            "type": "rpm",
            "name": "RHEL 8",
            "baseos": "https://mirrors.aliyun.com/centos/8-stream/BaseOS/x86_64/os/",
            "arch": "x86_64",
        },
        "fedora": {
            "type": "rpm",
            "name": "Fedora",
            "baseos": "https://mirrors.aliyun.com/fedora/releases/39/Everything/x86_64/os/",
            "arch": "x86_64",
        },
        # DEB 发行版
        "ubuntu-20": {
            "type": "deb",
            "name": "Ubuntu 20.04 LTS (Focal)",
            "main": "http://archive.ubuntu.com/ubuntu/dists/focal/main/",
            "arch": "amd64",
        },
        "ubuntu-22": {
            "type": "deb",
            "name": "Ubuntu 22.04 LTS (Jammy)",
            "main": "http://archive.ubuntu.com/ubuntu/dists/jammy/main/",
            "arch": "amd64",
        },
        "ubuntu-24": {
            "type": "deb",
            "name": "Ubuntu 24.04 LTS (Noble)",
            "main": "http://archive.ubuntu.com/ubuntu/dists/noble/main/",
            "arch": "amd64",
        },
        "debian-11": {
            "type": "deb",
            "name": "Debian 11 (Bullseye)",
            "main": "http://deb.debian.org/debian/dists/bullseye/main/",
            "arch": "amd64",
        },
        "debian-12": {
            "type": "deb",
            "name": "Debian 12 (Bookworm)",
            "main": "http://deb.debian.org/debian/dists/bookworm/main/",
            "arch": "amd64",
        },
    }

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
