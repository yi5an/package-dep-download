#!/bin/bash
##############################################################################
# DEB 系统示例: 下载 Web 服务器及其依赖
##############################################################################

# 下载 Apache
./offline-installer.sh -t deb apache2

# 下载完整的 LEMP 栈
./offline-installer.sh -t deb -o lemp-stack \
    nginx \
    mysql-server \
    php-fpm \
    php-mysql

# 下载开发工具
./offline-installer.sh -t deb -o dev-tools \
    build-essential \
    git \
    vim \
    python3 \
    python3-pip \
    nodejs \
    npm
