# 快速开始指南

## 5 分钟上手

### 步骤 1: 准备工具 (仅第一次需要)

**RPM 系统 (CentOS/RHEL/Fedora):**
```bash
# CentOS/RHEL 8+, Fedora
sudo dnf install dnf-plugins-core

# CentOS/RHEL 7
sudo yum install yum-utils
```

**DEB 系统 (Debian/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install apt-rdepends
```

### 步骤 2: 下载包及其依赖

**RPM 示例 - 下载 Docker:**
```bash
./offline-installer.sh -t rpm docker-ce
```

**DEB 示例 - 下载 Nginx:**
```bash
./offline-installer.sh -t deb nginx
```

### 步骤 3: 打包并传输

```bash
cd packages
./make-tarball.sh

# 传输到离线机器
scp offline-packages-*.tar.gz user@offline-machine:/tmp/
```

### 步骤 4: 在离线机器上安装

```bash
cd /tmp
tar -xzf offline-packages-*.tar.gz
cd packages
sudo ./install.sh
```

## 常用命令速查

### RPM 系统

| 需求 | 命令 |
|------|------|
| 下载单个包 | `./offline-installer.sh -t rpm nginx` |
| 下载多个包 | `./offline-installer.sh -t rpm nginx mysql redis` |
| 递归下载所有依赖 | `./offline-installer.sh -t rpm -d docker-ce` |
| 指定输出目录 | `./offline-installer.sh -t rpm -o /tmp/packages nginx` |

### DEB 系统

| 需求 | 命令 |
|------|------|
| 下载单个包 | `./offline-installer.sh -t deb apache2` |
| 下载多个包 | `./offline-installer.sh -t deb nginx mysql php` |
| 递归下载所有依赖 | `./offline-installer.sh -t deb -d docker.io` |
| 指定输出目录 | `./offline-installer.sh -t deb -o /tmp/packages nginx` |

## 实战案例

### 案例 1: 离线环境部署 Docker

**需求**: 在没有外网的服务器上安装 Docker

**解决方案**:
```bash
# 1. 在有网络的机器上下载
./offline-installer.sh -t rpm -d -o docker-offline docker-ce docker-ce-cli containerd.io

# 2. 打包
cd docker-offline
./make-tarball.sh

# 3. 传输到离线服务器
scp offline-packages-*.tar.gz root@offline-server:/tmp/

# 4. 在离线服务器上安装
ssh root@offline-server
cd /tmp
tar -xzf offline-packages-*.tar.gz
cd docker-offline
sudo ./install.sh
```

### 案例 2: 离线环境部署 Web 服务

**CentOS/RHEL:**
```bash
./offline-installer.sh -t rpm -o web-server nginx
```

**Ubuntu/Debian:**
```bash
./offline-installer.sh -t deb -o web-server apache2
```

### 案例 3: 批量下载开发工具

1. 创建包列表文件 `my-tools.list`:
```bash
git
vim
gcc
gcc-c++
make
cmake
python3
nodejs
```

2. 批量下载:
```bash
./offline-installer.sh -t rpm $(cat my-tools.list)
```

### 案例 4: 跨架构下载

**场景**: 在 x86_64 机器上为 ARM64 服务器下载包

```bash
./offline-installer.sh -t rpm -a aarch64 nginx
```

## 常见问题快速解决

### 问题: 提示缺少工具

**RPM 系统**:
```bash
sudo dnf install dnf-plugins-core  # CentOS/RHEL 8+
# 或
sudo yum install yum-utils          # CentOS/RHEL 7
```

**DEB 系统**:
```bash
sudo apt-get install apt-rdepends
```

### 问题: 下载不完整

解决方法: 使用 `-d` 参数递归下载
```bash
./offline-installer.sh -t rpm -d <package-name>
```

### 问题: 安装时依赖冲突

解决方法:
1. 确保在线和离线机器系统版本一致
2. 使用 `-d` 参数下载所有依赖
3. 检查架构是否匹配

### 问题: 找不到某个包

解决方法:
1. 检查包名是否正确
2. 检查软件源是否启用
3. 尝试搜索: `yum search <keyword>` 或 `apt search <keyword>`

## 最佳实践

1. ✅ **使用相同的系统版本**: 在线机器和离线机器使用相同版本的操作系统
2. ✅ **使用递归下载**: 对于复杂软件,使用 `-d` 参数确保下载所有依赖
3. ✅ **测试安装**: 先在测试环境验证安装流程
4. ✅ **保存下载记录**: 记录成功下载的包列表,便于重复使用
5. ✅ **定期更新**: 软件包会更新,定期重新下载最新版本

## 下一步

- 阅读完整的 [README.md](README.md) 了解更多功能
- 查看 [examples/](examples/) 目录中的示例脚本
- 根据实际需求定制下载流程

## 获取帮助

查看完整帮助信息:
```bash
./offline-installer.sh -h
```
