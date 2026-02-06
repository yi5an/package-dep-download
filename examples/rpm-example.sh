#!/bin/bash
##############################################################################
# RPM 系统示例: 下载 Docker 及其所有依赖
##############################################################################

# 基础用法
./offline-installer.sh -t rpm docker-ce

# 递归下载所有依赖(包括已安装的)
./offline-installer.sh -t rpm -d docker-ce

# 指定输出目录
./offline-installer.sh -t rpm -o docker-packages docker-ce docker-ce-cli containerd.io

# 下载完整的容器环境
./offline-installer.sh -t rpm -o container-env \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-compose-plugin
