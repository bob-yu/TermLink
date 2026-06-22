#!/bin/bash
# Linux/Ubuntu 打包脚本
# 用法: chmod +x build.sh && ./build.sh
# 选项: ./build.sh [onefile|clean|deb|help]

set -e

# 版本号
VERSION="1.0.5"
APP_NAME="TermLink"
APP_DESC="Terminal tool for serial, SSH, Telnet, and remote serial access"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================"
echo "  $APP_NAME v$VERSION 打包脚本"
echo "  平台: Linux/Ubuntu"
echo "========================================"
echo

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python3
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo_error "未找到 Python3，请先安装"
        echo "  Ubuntu: sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi
    echo_info "Python3: $(python3 --version)"
}

# 检查并安装依赖
check_dependencies() {
    echo_info "检查依赖..."
    
    # 检查 pip
    if ! python3 -m pip --version &> /dev/null; then
        echo_error "未找到 pip，请安装: sudo apt install python3-pip"
        exit 1
    fi
    
    # 检查 PyInstaller
    if ! python3 -c "import PyInstaller" &> /dev/null 2>&1; then
        echo_warn "PyInstaller 未安装，正在安装..."
        python3 -m pip install --user pyinstaller
    fi
    
    # 检查项目依赖
    local deps=("PyQt5" "serial" "pyte" "paramiko")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! python3 -c "import $dep" &> /dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo_warn "缺少依赖: ${missing[*]}"
        echo_info "安装依赖..."
        python3 -m pip install --user -r requirements.txt
    fi
    
    echo_info "依赖检查完成"
}

# 清理
clean() {
    echo_info "清理临时文件..."
    rm -rf build/ dist/ __pycache__/ release/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo_info "清理完成"
}

# 打包成目录
build_dir() {
    echo_info "开始打包（目录模式）..."
    
    python3 -m PyInstaller \
        --name "$APP_NAME" \
        --windowed \
        --onedir \
        --noconfirm \
        --clean \
        --hidden-import PyQt5.sip \
        --hidden-import PyQt5.QtCore \
        --hidden-import PyQt5.QtGui \
        --hidden-import PyQt5.QtWidgets \
        --hidden-import serial \
        --hidden-import serial.tools \
        --hidden-import serial.tools.list_ports \
        --hidden-import serial.tools.list_ports_common \
        --hidden-import serial.tools.list_ports_linux \
        --hidden-import serial.tools.list_ports_posix \
        --hidden-import pyte \
        --hidden-import pyte.screens \
        --hidden-import pyte.streams \
        --hidden-import pyte.graphics \
        --hidden-import pyte.modes \
        --hidden-import paramiko \
        --hidden-import paramiko.transport \
        --hidden-import paramiko.channel \
        --hidden-import paramiko.client \
        --hidden-import paramiko.ssh_exception \
        --hidden-import cryptography \
        --hidden-import cryptography.hazmat.primitives.ciphers \
        --hidden-import cffi \
        --hidden-import nacl \
        --hidden-import bcrypt \
        --exclude-module PyQt5.QtBluetooth \
        --exclude-module PyQt5.QtDesigner \
        --exclude-module PyQt5.QtHelp \
        --exclude-module PyQt5.QtLocation \
        --exclude-module PyQt5.QtMultimedia \
        --exclude-module PyQt5.QtMultimediaWidgets \
        --exclude-module PyQt5.QtNetworkAuth \
        --exclude-module PyQt5.QtNfc \
        --exclude-module PyQt5.QtOpenGL \
        --exclude-module PyQt5.QtPositioning \
        --exclude-module PyQt5.QtQml \
        --exclude-module PyQt5.QtQuick \
        --exclude-module PyQt5.QtQuickWidgets \
        --exclude-module PyQt5.QtSql \
        --exclude-module PyQt5.QtSvg \
        --exclude-module PyQt5.QtTest \
        --exclude-module PyQt5.QtWebChannel \
        --exclude-module PyQt5.QtWebEngine \
        --exclude-module PyQt5.QtWebEngineCore \
        --exclude-module PyQt5.QtWebEngineWidgets \
        --exclude-module PyQt5.QtXmlPatterns \
        --exclude-module tkinter \
        --exclude-module unittest \
        --exclude-module pydoc \
        --add-data "config.example.json:." \
        main.py
    
    # 创建 logs 目录
    mkdir -p "dist/$APP_NAME/logs"
    
    # Copy the default template if it was not collected by PyInstaller.
    if [ -f "config.example.json" ] && [ ! -f "dist/$APP_NAME/config.example.json" ]; then
        cp config.example.json "dist/$APP_NAME/"
    fi
}

# 打包成单文件
build_onefile() {
    echo_info "开始打包（单文件模式）..."
    
    python3 -m PyInstaller \
        --name "$APP_NAME" \
        --windowed \
        --onefile \
        --noconfirm \
        --clean \
        --hidden-import PyQt5.sip \
        --hidden-import PyQt5.QtCore \
        --hidden-import PyQt5.QtGui \
        --hidden-import PyQt5.QtWidgets \
        --hidden-import serial \
        --hidden-import serial.tools \
        --hidden-import serial.tools.list_ports \
        --hidden-import serial.tools.list_ports_common \
        --hidden-import serial.tools.list_ports_linux \
        --hidden-import serial.tools.list_ports_posix \
        --hidden-import pyte \
        --hidden-import pyte.screens \
        --hidden-import pyte.streams \
        --hidden-import pyte.graphics \
        --hidden-import pyte.modes \
        --hidden-import paramiko \
        --hidden-import paramiko.transport \
        --hidden-import paramiko.channel \
        --hidden-import paramiko.client \
        --hidden-import paramiko.ssh_exception \
        --hidden-import cryptography \
        --hidden-import cryptography.hazmat.primitives.ciphers \
        --exclude-module PyQt5.QtBluetooth \
        --exclude-module PyQt5.QtDesigner \
        --exclude-module PyQt5.QtHelp \
        --exclude-module PyQt5.QtLocation \
        --exclude-module PyQt5.QtMultimedia \
        --exclude-module PyQt5.QtMultimediaWidgets \
        --exclude-module PyQt5.QtNetworkAuth \
        --exclude-module PyQt5.QtNfc \
        --exclude-module PyQt5.QtOpenGL \
        --exclude-module PyQt5.QtPositioning \
        --exclude-module PyQt5.QtQml \
        --exclude-module PyQt5.QtQuick \
        --exclude-module PyQt5.QtQuickWidgets \
        --exclude-module PyQt5.QtSql \
        --exclude-module PyQt5.QtSvg \
        --exclude-module PyQt5.QtTest \
        --exclude-module PyQt5.QtWebChannel \
        --exclude-module PyQt5.QtWebEngine \
        --exclude-module PyQt5.QtWebEngineCore \
        --exclude-module PyQt5.QtWebEngineWidgets \
        --exclude-module PyQt5.QtXmlPatterns \
        --exclude-module tkinter \
        --exclude-module unittest \
        --exclude-module pydoc \
        --add-data "config.example.json:." \
        main.py
}

# 创建发布包
create_release() {
    local mode=$1
    local release_name="${APP_NAME}_v${VERSION}_linux_amd64"
    
    echo_info "创建发布包..."
    mkdir -p release
    
    if [ "$mode" = "onefile" ]; then
        # 单文件模式
        mkdir -p "release/$release_name"
        cp "dist/$APP_NAME" "release/$release_name/"
        cp config.example.json "release/$release_name/" 2>/dev/null || true
        mkdir -p "release/$release_name/logs"
        
        # 创建启动脚本
        cat > "release/$release_name/run.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./$APP_NAME
EOF
        sed -i "s/\$APP_NAME/$APP_NAME/g" "release/$release_name/run.sh"
        chmod +x "release/$release_name/run.sh"
        chmod +x "release/$release_name/$APP_NAME"
    else
        # 目录模式
        cp -r "dist/$APP_NAME" "release/$release_name"
        chmod +x "release/$release_name/$APP_NAME"
    fi
    
    # 创建 tar.gz 包
    cd release
    tar -czvf "${release_name}.tar.gz" "$release_name"
    cd ..
    
    echo_info "发布包: release/${release_name}.tar.gz"
}

# 创建 .deb 包
build_deb() {
    echo_info "创建 .deb 安装包..."
    
    # 先打包
    build_dir
    
    local deb_name="${APP_NAME,,}"  # 转小写
    local arch=$(dpkg --print-architecture 2>/dev/null || echo "amd64")
    local deb_dir="release/${deb_name}_${VERSION}_${arch}"
    
    # 计算安装后大小 (KB)
    local installed_size=$(du -sk "dist/$APP_NAME" | cut -f1)
    
    mkdir -p "$deb_dir/DEBIAN"
    mkdir -p "$deb_dir/opt/$APP_NAME"
    mkdir -p "$deb_dir/usr/share/applications"
    mkdir -p "$deb_dir/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$deb_dir/usr/share/doc/${deb_name}"
    
    # 复制程序文件
    cp -r "dist/$APP_NAME/"* "$deb_dir/opt/$APP_NAME/"
    chmod +x "$deb_dir/opt/$APP_NAME/$APP_NAME"
    
    # 创建 logs 目录（安装后用户可写）
    mkdir -p "$deb_dir/opt/$APP_NAME/logs"
    chmod 777 "$deb_dir/opt/$APP_NAME/logs"
    
    # 创建 control 文件
    cat > "$deb_dir/DEBIAN/control" << EOF
Package: ${deb_name}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${arch}
Installed-Size: ${installed_size}
Depends: libxcb-xinerama0, libxcb-cursor0, libxkbcommon0, libgl1
Recommends: python3
Maintainer: TermLink Team <support@example.com>
Homepage: https://github.com/example/termlink
Description: ${APP_DESC}
 TermLink is a desktop terminal tool for embedded development, hardware
 bring-up, production debugging, and remote device access.
 .
 Main features:
  - Local serial terminals with professional line settings
  - SSH and Telnet terminal sessions
  - Remote serial access through one Serial Access service
  - CLI and MCP automation adapters
  - Runtime diagnostics, per-session logs, command sets, find, highlight, and watch
EOF
    
    # 创建 .desktop 文件
    cat > "$deb_dir/usr/share/applications/${deb_name}.desktop" << EOF
[Desktop Entry]
Name=TermLink
GenericName=Serial Port Tool
Comment=${APP_DESC}
Exec=/opt/$APP_NAME/$APP_NAME
Icon=${deb_name}
Terminal=false
Type=Application
Categories=Development;Utility;Electronics;
Keywords=serial;uart;com;port;terminal;ssh;
StartupNotify=true
EOF
    
    # 复制图标
    if [ -f "assets/app-icon.png" ]; then
        cp assets/app-icon.png "$deb_dir/usr/share/icons/hicolor/256x256/apps/${deb_name}.png"
    fi
    
    # 复制文档
    if [ -f "README.md" ]; then
        cp README.md "$deb_dir/usr/share/doc/${deb_name}/"
    fi
    if [ -f "CHANGELOG.md" ]; then
        cp CHANGELOG.md "$deb_dir/usr/share/doc/${deb_name}/"
    fi
    
    # 创建 copyright 文件
    cat > "$deb_dir/usr/share/doc/${deb_name}/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: ${APP_NAME}
Source: https://github.com/example/termlink

Files: *
Copyright: 2024-2026 TermLink Team
License: MIT
EOF
    
    # 创建 postinst 脚本
    cat > "$deb_dir/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

# 创建符号链接
ln -sf /opt/TermLink/TermLink /usr/local/bin/termlink

# 更新图标缓存
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 更新桌面数据库
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

# 添加用户到 dialout 组（串口访问权限）
if [ -n "$SUDO_USER" ]; then
    usermod -a -G dialout "$SUDO_USER" 2>/dev/null || true
    echo "提示: 用户 $SUDO_USER 已添加到 dialout 组，重新登录后生效"
fi

echo ""
echo "TermLink 安装完成!"
echo "  - 从应用菜单启动，或运行: termlink"
echo "  - 如需串口访问权限，请重新登录或运行: newgrp dialout"
echo ""

exit 0
POSTINST
    chmod 755 "$deb_dir/DEBIAN/postinst"
    
    # 创建 prerm 脚本
    cat > "$deb_dir/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
set -e
rm -f /usr/local/bin/termlink
exit 0
PRERM
    chmod 755 "$deb_dir/DEBIAN/prerm"
    
    # 创建 postrm 脚本
    cat > "$deb_dir/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
set -e

# 更新图标缓存
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 更新桌面数据库
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

exit 0
POSTRM
    chmod 755 "$deb_dir/DEBIAN/postrm"
    
    # 设置正确的权限
    find "$deb_dir" -type d -exec chmod 755 {} \;
    find "$deb_dir/opt" -type f -exec chmod 644 {} \;
    chmod 755 "$deb_dir/opt/$APP_NAME/$APP_NAME"
    chmod 755 "$deb_dir/opt/$APP_NAME/logs"
    
    # 构建 deb 包
    mkdir -p release
    
    echo_info "构建 deb 包..."
    if command -v fakeroot &> /dev/null; then
        fakeroot dpkg-deb --build "$deb_dir"
    else
        dpkg-deb --build "$deb_dir"
    fi
    
    mv "${deb_dir}.deb" "release/"
    rm -rf "$deb_dir"
    
    local deb_file="release/${deb_name}_${VERSION}_${arch}.deb"
    local deb_size=$(du -h "$deb_file" | cut -f1)
    
    echo
    echo "========================================"
    echo_info "DEB 包创建成功!"
    echo "========================================"
    echo "  文件: $deb_file"
    echo "  大小: $deb_size"
    echo
    echo "安装命令:"
    echo "  sudo dpkg -i $deb_file"
    echo "  sudo apt-get install -f  # 如有依赖问题"
    echo
    echo "卸载命令:"
    echo "  sudo apt remove ${deb_name}"
    echo "========================================"
}

# 显示帮助
show_help() {
    cat << EOF
$APP_NAME v$VERSION 打包脚本

用法:
    ./build.sh              # 打包成目录（推荐，启动快）
    ./build.sh onefile      # 打包成单个可执行文件
    ./build.sh deb          # 创建 .deb 安装包 (Ubuntu/Debian)
    ./build.sh clean        # 清理临时文件
    ./build.sh help         # 显示帮助

依赖安装 (Ubuntu):
    sudo apt install python3 python3-pip python3-venv
    pip3 install --user pyinstaller PyQt5 pyserial pyte paramiko

输出:
    dist/$APP_NAME/         # 打包后的程序目录
    release/                # 发布包目录

EOF
}

# 主函数
main() {
    local cmd="${1:-build}"
    
    case "$cmd" in
        clean)
            clean
            ;;
        onefile)
            check_python
            check_dependencies
            clean
            build_onefile
            create_release "onefile"
            echo
            echo_info "打包完成！"
            echo "  可执行文件: dist/$APP_NAME"
            echo "  发布包: release/${APP_NAME}_v${VERSION}_linux_amd64.tar.gz"
            ;;
        deb)
            check_python
            check_dependencies
            clean
            build_deb
            echo
            echo_info "打包完成！"
            ;;
        help|-h|--help)
            show_help
            ;;
        build|*)
            check_python
            check_dependencies
            clean
            build_dir
            create_release "dir"
            echo
            echo_info "打包完成！"
            echo "  程序目录: dist/$APP_NAME/"
            echo "  可执行文件: dist/$APP_NAME/$APP_NAME"
            echo "  发布包: release/${APP_NAME}_v${VERSION}_linux_amd64.tar.gz"
            ;;
    esac
}

main "$@"

