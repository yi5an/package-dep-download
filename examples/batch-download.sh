#!/bin/bash
##############################################################################
# 批量下载示例: 从文件读取包列表
##############################################################################

PACKAGES_FILE="packages.list"

# 检查文件是否存在
if [ ! -f "$PACKAGES_FILE" ]; then
    echo "错误: 找不到 $PACKAGES_FILE"
    exit 1
fi

echo "=========================================="
echo "批量离线包下载工具"
echo "=========================================="
echo ""
echo "请选择包类型:"
echo "1) RPM (CentOS/RHEL/Fedora)"
echo "2) DEB (Debian/Ubuntu)"
echo ""
read -p "请输入选择 (1/2): " choice

case $choice in
    1)
        PKG_TYPE="rpm"
        echo "已选择: RPM 系统"
        ;;
    2)
        PKG_TYPE="deb"
        echo "已选择: DEB 系统"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
read -p "输出目录 (默认: ./packages): " output_dir
output_dir=${output_dir:-./packages}

echo ""
read -p "是否递归下载所有依赖? (y/N): " deep
if [[ $deep =~ ^[Yy]$ ]]; then
    DEEP_FLAG="-d"
    echo "已启用递归下载"
else
    DEEP_FLAG=""
    echo "未启用递归下载"
fi

echo ""
echo "=========================================="
echo "配置信息:"
echo "  包类型: $PKG_TYPE"
echo "  输出目录: $output_dir"
echo "  递归下载: $([ -n "$DEEP_FLAG" ] && echo "是" || echo "否")"
echo ""
echo "将要下载的包:"
cat "$PACKAGES_FILE" | while read pkg; do
    [ -n "$pkg" ] && echo "  - $pkg"
done
echo "=========================================="
echo ""
read -p "确认开始下载? (Y/n): " confirm

if [[ $confirm =~ ^[Nn]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始下载..."
./offline-installer.sh -t $PKG_TYPE -o "$output_dir" $DEEP_FLAG $(cat "$PACKAGES_FILE" | tr '\n' ' ')

echo ""
echo "完成!"
