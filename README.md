# 离线软件包依赖下载工具

## 简介

这是一个强大的离线软件包依赖下载工具,支持 RPM 和 DEB 包系统。它可以自动解析并下载指定软件包的所有依赖项,方便在离线环境中安装软件。

## 特性

- ✅ 支持 RPM 系统(CentOS, RHEL, Fedora, Rocky Linux, AlmaLinux 等)
- ✅ 支持 DEB 系统(Debian, Ubuntu 等)
- ✅ 自动递归下载所有依赖包
- ✅ 自动生成离线安装脚本
- ✅ 自动生成打包脚本
- ✅ 支持自定义输出目录
- ✅ 支持多架构(x86_64, aarch64, arm64)
- ✅ 提供详细的下载日志和统计信息

## 系统要求

### RPM 系统
- CentOS/RHEL 7+: 需要 `yum-utils`
- CentOS/RHEL 8+/Fedora: 需要 `dnf-plugins-core`

安装命令:
```bash
# CentOS/RHEL 8+, Fedora
sudo dnf install dnf-plugins-core

# CentOS/RHEL 7
sudo yum install yum-utils
```

### DEB 系统
- Debian/Ubuntu: 需要 `apt-rdepends`

安装命令:
```bash
sudo apt-get update
sudo apt-get install apt-rdepends
```

## 使用方法

### 基本语法

```bash
./offline-installer.sh [选项] <包名列表>
```

### 选项说明

| 选项 | 说明 |
|------|------|
| `-t, --type TYPE` | 包类型 (rpm\|deb) [必需] |
| `-o, --output DIR` | 输出目录 [默认: ./packages] |
| `-a, --arch ARCH` | 架构 (x86_64\|aarch64\|arm64) [默认: 自动检测] |
| `-d, --deep` | 递归下载所有依赖(包括已安装的) |
| `-h, --help` | 显示帮助信息 |
| `-v, --version` | 显示版本信息 |

### 使用示例

#### 1. 下载 RPM 包及其依赖

```bash
# 下载 nginx 及其依赖
./offline-installer.sh -t rpm nginx

# 下载多个包
./offline-installer.sh -t rpm nginx python3 nodejs

# 指定输出目录
./offline-installer.sh -t rpm -o /tmp/docker-packages docker-ce

# 递归下载所有依赖(包括已安装的包)
./offline-installer.sh -t rpm -d docker-ce
```

#### 2. 下载 DEB 包及其依赖

```bash
# 下载 apache2 及其依赖
./offline-installer.sh -t deb apache2

# 下载多个包到指定目录
./offline-installer.sh -t deb -o /tmp/web-packages apache2 mysql-server php

# 递归下载
./offline-installer.sh -t deb -d nginx
```

## 工作流程

### 在线机器上

1. **下载包及其依赖**
```bash
./offline-installer.sh -t rpm nginx
```

2. **打包以便传输**
```bash
cd packages
./make-tarball.sh
```

3. **传输到离线机器**
```bash
scp offline-packages-*.tar.gz user@offline-machine:/tmp/
```

### 在离线机器上

1. **解压**
```bash
cd /tmp
tar -xzf offline-packages-*.tar.gz
cd packages
```

2. **安装**
```bash
./install.sh
```

## 目录结构

下载完成后,输出目录结构如下:

```
packages/
├── nginx-1.20.1-1.el8.x86_64.rpm
├── openssl-libs-1.1.1k-4.el8.x86_64.rpm
├── glibc-2.28-151.el8.x86_64.rpm
├── ... (其他依赖包)
├── install.sh          # 离线安装脚本
└── make-tarball.sh     # 打包脚本
```

## 实际应用场景

### 场景 1: 离线环境安装 Docker

```bash
# 在线机器上下载
./offline-installer.sh -t rpm -d -o docker-offline docker-ce docker-ce-cli containerd.io

# 打包
cd docker-offline
./make-tarball.sh

# 传输到离线机器并安装
tar -xzf offline-packages-*.tar.gz
cd docker-offline
sudo ./install.sh
```

### 场景 2: 离线环境安装 Web 服务器

```bash
# CentOS/RHEL
./offline-installer.sh -t rpm -o web-server nginx

# Ubuntu/Debian
./offline-installer.sh -t deb -o web-server apache2
```

### 场景 3: 批量下载开发工具

```bash
# 下载常用的开发工具
./offline-installer.sh -t rpm -o dev-tools \
    git vim gcc gcc-c++ make cmake \
    python3 python3-pip nodejs
```

## 常见问题

### Q1: 下载失败怎么办?

**A:** 检查以下几点:
- 确保网络连接正常
- 检查软件源配置是否正确
- 尝试使用 `--deep` 参数
- 检查包名是否正确

### Q2: 有些包下载不下来?

**A:** 可能的原因:
- 包名不存在或拼写错误
- 该包不在当前启用的软件源中
- 可以尝试先手动下载: `yumdownloader <包名>` 或 `apt-get download <包名>`

### Q3: 安装时提示依赖冲突?

**A:** 离线环境可能缺少某些基础包,建议:
- 使用与在线环境相同的系统版本
- 使用 `-d` 参数递归下载所有依赖
- 检查系统版本兼容性

### Q4: 如何跨架构使用?

**A:** 使用 `-a` 参数指定目标架构:
```bash
# 为 ARM64 机器下载包(x86_64 机器上)
./offline-installer.sh -t rpm -a aarch64 nginx
```

## 注意事项

1. **系统版本匹配**: 确保在线和离线机器使用相同或兼容的系统版本
2. **架构匹配**: 确保下载的包架构与目标机器一致
3. **软件源一致**: 建议使用相同的软件源配置
4. **磁盘空间**: 某些大型软件(如 Docker)可能需要下载数百 MB 的依赖
5. **权限**: 安装脚本需要 sudo 权限

## 高级技巧

### 1. 批量下载多个包

创建一个包列表文件:

```bash
# packages.list
nginx
mysql-server
redis
python3
```

然后批量下载:

```bash
./offline-installer.sh -t rpm $(cat packages.list)
```

### 2. 下载特定版本的包

```bash
# RPM
./offline-installer.sh -t rpm nginx-1.18.0

# DEB
./offline-installer.sh -t deb apache2=2.4.41-4ubuntu3
```

### 3. 创建本地仓库

下载大量包后,可以创建本地仓库:

**RPM 系统:**
```bash
mkdir -p /local-repo
cp packages/*.rpm /local-repo/
createrepo /local-repo
```

**DEB 系统:**
```bash
mkdir -p /local-repo
cp packages/*.deb /local-repo/
dpkg-scanpackages /local-repo /dev/null | gzip > /local-repo/Packages.gz
```

## 贡献

欢迎提交 Issue 和 Pull Request!

## 许可证

MIT License

## 作者

Created with ❤️ for offline installations
