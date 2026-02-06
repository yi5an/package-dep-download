#!/bin/bash
##############################################################################
# 离线软件包依赖下载工具
# 支持 RPM (CentOS/RHEL/Fedora) 和 DEB (Debian/Ubuntu) 包系统
##############################################################################

set -e

VERSION="1.0.0"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印帮助信息
show_help() {
    cat << EOF
离线软件包依赖下载工具 v${VERSION}

用法:
    $0 [选项] <包名列表>

选项:
    -t, --type TYPE        包类型 (rpm|deb) [必需]
    -o, --output DIR       输出目录 [默认: ./packages]
    -r, --repo URL         仓库 URL (可选,用于自定义仓库)
    -a, --arch ARCH        架构 (x86_64|aarch64|arm64) [默认: 自动检测]
    -d, --deep             递归下载所有依赖(包括已安装的)
    -h, --help             显示此帮助信息
    -v, --version          显示版本信息

示例:
    # 下载 RPM 包及其依赖
    $0 -t rpm nginx python3

    # 下载 DEB 包及其依赖到指定目录
    $0 -t deb -o /tmp/packages apache2 mysql-server

    # 递归下载所有依赖(包括已安装的包)
    $0 -t rpm -d docker-ce

RPM 系统要求: yum-utils 或 dnf-plugins-core
DEB 系统要求: apt-rdepends

EOF
}

# 打印日志
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测系统架构
detect_arch() {
    case $(uname -m) in
        x86_64)
            echo "x86_64"
            ;;
        aarch64|arm64)
            echo "aarch64"
            ;;
        i386|i686)
            echo "i386"
            ;;
        *)
            log_error "不支持的架构: $(uname -m)"
            exit 1
            ;;
    esac
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        return 1
    fi
    return 0
}

# 下载 RPM 包及其依赖
download_rpm() {
    local packages=$@
    local output_dir=$OUTPUT_DIR
    local deep=$DEEP_DOWNLOAD

    log_info "开始下载 RPM 包..."

    # 检查必要工具
    if check_command dnf; then
        DOWNLOAD_CMD="dnf download"
        RESOLVE_CMD="dnf repoquery --requires --resolve"
    elif check_command yumdownloader; then
        DOWNLOAD_CMD="yumdownloader"
        RESOLVE_CMD="repoquery --requires --resolve"
    else
        log_error "未找到必要的工具,请安装: dnf-plugins-core 或 yum-utils"
        log_info "安装命令:"
        log_info "  CentOS/RHEL 8+: sudo dnf install dnf-plugins-core"
        log_info "  CentOS/RHEL 7: sudo yum install yum-utils"
        exit 1
    fi

    # 创建输出目录
    mkdir -p "$output_dir"

    # 下载主包
    log_info "下载主包: $packages"
    $DOWNLOAD_CMD --destdir="$output_dir" $packages || true

    # 递归下载依赖
    if [ "$deep" = "true" ]; then
        log_info "使用 repotrack 递归下载所有依赖..."
        if check_command repotrack; then
            repotrack --arch=$ARCH -p "$output_dir/" $packages
        else
            log_warn "repotrack 未找到,使用基础方式下载依赖"
            download_rpm_deps "$packages" "$output_dir"
        fi
    else
        download_rpm_deps "$packages" "$output_dir"
    fi

    log_info "下载完成!文件保存在: $output_dir"
}

# 递归下载 RPM 依赖
download_rpm_deps() {
    local packages=$1
    local output_dir=$2
    local processed=""

    log_info "解析依赖关系..."

    # 获取所有未安装的依赖
    local deps=$(repoquery --requires --resolve --recursive $packages 2>/dev/null | grep -v "^[ ]*$" | sort -u || true)

    if [ -z "$deps" ]; then
        log_warn "未找到额外依赖或所有依赖已安装"
        return
    fi

    log_info "找到依赖包:"
    echo "$deps" | while read pkg; do
        [ -n "$pkg" ] && echo "  - $pkg"
    done

    # 下载依赖包
    log_info "下载依赖包..."
    for pkg in $deps; do
        if [ -n "$pkg" ]; then
            log_info "  下载: $pkg"
            $DOWNLOAD_CMD --destdir="$output_dir" $pkg 2>/dev/null || true
        fi
    done
}

# 下载 DEB 包及其依赖
download_deb() {
    local packages=$@
    local output_dir=$OUTPUT_DIR

    log_info "开始下载 DEB 包..."

    # 检查必要工具
    if ! check_command apt-get; then
        log_error "这不是 Debian/Ubuntu 系统"
        exit 1
    fi

    # 检查 apt-rdepends
    if ! check_command apt-rdepends; then
        log_warn "apt-rdepends 未安装"
        log_info "正在安装 apt-rdepends..."
        sudo apt-get update
        sudo apt-get install -y apt-rdepends
    fi

    # 创建输出目录
    mkdir -p "$output_dir"

    cd "$output_dir"

    # 获取所有依赖包列表
    log_info "解析依赖关系..."
    local all_deps=$(apt-rdepends $packages 2>/dev/null | grep -v "^[ ]*$" | grep -v "^PreDepends" | grep -v "^Depends" | grep -v "^Recommends" | grep -v "^Suggests" | sort -u)

    if [ -z "$all_deps" ]; then
        log_error "无法解析依赖"
        exit 1
    fi

    log_info "找到以下包及依赖:"
    echo "$all_deps" | while read pkg; do
        [ -n "$pkg" ] && echo "  - $pkg"
    done

    # 下载所有包
    log_info "开始下载..."
    for pkg in $all_deps; do
        if [ -n "$pkg" ]; then
            log_info "  下载: $pkg"
            apt-get download $pkg 2>/dev/null || log_warn "    跳过: $pkg (可能已安装或不存在)"
        fi
    done

    cd - > /dev/null

    log_info "下载完成!文件保存在: $output_dir"
}

# 生成安装脚本
generate_install_script() {
    local output_dir=$1
    local pkg_type=$2

    local install_script="$output_dir/install.sh"

    cat > "$install_script" << 'INSTALLEOF'
#!/bin/bash
##############################################################################
# 离线安装脚本
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

INSTALLEOF

    if [ "$pkg_type" = "rpm" ]; then
        cat >> "$install_script" << 'EOF'

log_info "开始安装 RPM 包..."

if [ -e "$SCRIPT_DIR"/*.rpm ]; then
    # 先安装依赖
    log_info "安装依赖包..."
    sudo rpm -Uvh --force --nodeps "$SCRIPT_DIR"/*.rpm 2>/dev/null || true

    # 重新安装以正确处理依赖
    log_info "重新安装包以处理依赖关系..."
    sudo rpm -Uvh --force "$SCRIPT_DIR"/*.rpm || \
    sudo yum localinstall -y "$SCRIPT_DIR"/*.rpm || \
    sudo dnf localinstall -y "$SCRIPT_DIR"/*.rpm

    log_info "安装完成!"
else
    log_error "未找到 RPM 包"
    exit 1
fi
EOF
    else
        cat >> "$install_script" << 'EOF'

log_info "开始安装 DEB 包..."

if [ -e "$SCRIPT_DIR"/*.deb ]; then
    # 安装所有包
    log_info "安装 DEB 包..."
    sudo dpkg -i "$SCRIPT_DIR"/*.deb || true

    # 修复依赖问题
    log_info "修复依赖..."
    sudo apt-get install -f -y

    log_info "安装完成!"
else
    log_error "未找到 DEB 包"
    exit 1
fi
EOF
    fi

    chmod +x "$install_script"
    log_info "已生成安装脚本: $install_script"
}

# 生成打包脚本
generate_package_script() {
    local output_dir=$1

    local tar_script="$output_dir/make-tarball.sh"

    cat > "$tar_script" << 'EOF'
#!/bin/bash
##############################################################################
# 打包脚本 - 将下载的包打包成 tar.gz
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="offline-packages-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "正在打包..."
cd "$SCRIPT_DIR/.."

tar -czf "$PACKAGE_NAME" -C "$(basename "$SCRIPT_DIR")" .

echo "打包完成: $PACKAGE_NAME"
echo "文件大小: $(du -h "$PACKAGE_NAME" | cut -f1)"
EOF

    chmod +x "$tar_script"
    log_info "已生成打包脚本: $tar_script"
}

# 主函数
main() {
    # 默认值
    OUTPUT_DIR="./packages"
    ARCH=$(detect_arch)
    DEEP_DOWNLOAD=false

    # 解析参数
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                PKG_TYPE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -r|--repo)
                REPO_URL="$2"
                shift 2
                ;;
            -a|--arch)
                ARCH="$2"
                shift 2
                ;;
            -d|--deep)
                DEEP_DOWNLOAD=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                echo "v${VERSION}"
                exit 0
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                PACKAGES="$@"
                break
                ;;
        esac
    done

    # 检查必要参数
    if [ -z "$PKG_TYPE" ]; then
        log_error "必须指定包类型 (-t|--type)"
        show_help
        exit 1
    fi

    if [ -z "$PACKAGES" ]; then
        log_error "必须指定至少一个包名"
        show_help
        exit 1
    fi

    # 验证包类型
    if [ "$PKG_TYPE" != "rpm" ] && [ "$PKG_TYPE" != "deb" ]; then
        log_error "不支持的包类型: $PKG_TYPE (支持: rpm, deb)"
        exit 1
    fi

    log_info "包类型: $PKG_TYPE"
    log_info "输出目录: $OUTPUT_DIR"
    log_info "架构: $ARCH"
    log_info "包列表: $PACKAGES"

    # 下载包
    case $PKG_TYPE in
        rpm)
            download_rpm $PACKAGES
            ;;
        deb)
            download_deb $PACKAGES
            ;;
    esac

    # 生成辅助脚本
    generate_install_script "$OUTPUT_DIR" "$PKG_TYPE"
    generate_package_script "$OUTPUT_DIR"

    # 显示统计信息
    log_info "==================== 统计信息 ===================="
    if [ "$PKG_TYPE" = "rpm" ]; then
        local count=$(ls -1 "$OUTPUT_DIR"/*.rpm 2>/dev/null | wc -l)
        local size=$(du -sh "$OUTPUT_DIR" 2>/dev/null | cut -f1)
    else
        local count=$(ls -1 "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l)
        local size=$(du -sh "$OUTPUT_DIR" 2>/dev/null | cut -f1)
    fi
    log_info "下载包数量: $count"
    log_info "总大小: $size"
    log_info "================================================="
}

main "$@"
