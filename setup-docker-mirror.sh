#!/bin/bash

# Docker 国内镜像源配置脚本

echo "配置 Docker 国内镜像源..."

# 创建配置目录
sudo mkdir -p /etc/docker

# 备份现有配置
if [ -f /etc/docker/daemon.json ]; then
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
fi

# 写入配置
sudo tee /etc/docker/daemon.json > /dev/null << 'JSONEOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
JSONEOF

# 重启 Docker
echo "重启 Docker 服务..."
sudo systemctl daemon-reload
sudo systemctl restart docker

echo "Docker 镜像源配置完成！"
docker info | grep -A 5 "Registry Mirrors"
