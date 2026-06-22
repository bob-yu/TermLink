#!/usr/bin/env python3
"""
PyInstaller 打包脚本
用法: python build.py
"""
import os
import sys
import shutil
import subprocess
import platform
import fnmatch

# 项目信息
APP_NAME = "TermLink"
VERSION = "1.0.5"
MAIN_SCRIPT = "main.py"
ICON_FILE = "assets/app-icon.ico" if os.path.exists("assets/app-icon.ico") else None

# PyInstaller 参数
PYINSTALLER_ARGS = [
    "--name", APP_NAME,
    "--windowed",           # 无控制台窗口（GUI程序）
    "--onedir",             # 打包成目录
    "--noconfirm",          # 覆盖已有输出
    "--clean",              # 清理临时文件

    # 隐藏导入
    "--hidden-import", "PyQt5",
    "--hidden-import", "PyQt5.sip",
    "--hidden-import", "PyQt5.QtCore",
    "--hidden-import", "PyQt5.QtGui",
    "--hidden-import", "PyQt5.QtWidgets",
    "--hidden-import", "serial",
    "--hidden-import", "serial.tools",
    "--hidden-import", "serial.tools.list_ports",
    "--hidden-import", "serial.tools.list_ports_common",
    "--hidden-import", "serial.tools.list_ports_windows",
    "--hidden-import", "serial.tools.list_ports_linux",
    "--hidden-import", "serial.tools.list_ports_posix",
    "--hidden-import", "pyte",
    "--hidden-import", "pyte.screens",
    "--hidden-import", "pyte.streams",
    "--hidden-import", "pyte.graphics",
    "--hidden-import", "pyte.modes",
    "--hidden-import", "paramiko",
    "--hidden-import", "paramiko.transport",
    "--hidden-import", "paramiko.channel",
    "--hidden-import", "paramiko.client",
    "--hidden-import", "paramiko.ssh_exception",
    "--hidden-import", "cryptography",
    "--hidden-import", "cryptography.hazmat.primitives.ciphers",
    "--hidden-import", "cffi",
    "--hidden-import", "nacl",
    "--hidden-import", "bcrypt",
    "--hidden-import", "queue",
    "--hidden-import", "threading",
    "--hidden-import", "json",
    "--hidden-import", "socket",
    "--hidden-import", "struct",
    "--hidden-import", "collections",
    "--hidden-import", "dataclasses",
    "--hidden-import", "enum",
    "--hidden-import", "typing",
    "--hidden-import", "re",
    "--hidden-import", "glob",
    "--hidden-import", "platform",
    "--hidden-import", "datetime",
    "--hidden-import", "time",
    "--hidden-import", "os",
    "--hidden-import", "sys",

    # 排除当前程序没有使用的 Qt/Python 模块，避免把 Qt 全家桶打进去
    "--exclude-module", "PyQt5.QtBluetooth",
    "--exclude-module", "PyQt5.QtDesigner",
    "--exclude-module", "PyQt5.QtHelp",
    "--exclude-module", "PyQt5.QtLocation",
    "--exclude-module", "PyQt5.QtMultimedia",
    "--exclude-module", "PyQt5.QtMultimediaWidgets",
    "--exclude-module", "PyQt5.QtNetworkAuth",
    "--exclude-module", "PyQt5.QtNfc",
    "--exclude-module", "PyQt5.QtOpenGL",
    "--exclude-module", "PyQt5.QtPositioning",
    "--exclude-module", "PyQt5.QtQml",
    "--exclude-module", "PyQt5.QtQuick",
    "--exclude-module", "PyQt5.QtQuickWidgets",
    "--exclude-module", "PyQt5.QtSql",
    "--exclude-module", "PyQt5.QtTest",
    "--exclude-module", "PyQt5.QtWebChannel",
    "--exclude-module", "PyQt5.QtWebEngine",
    "--exclude-module", "PyQt5.QtWebEngineCore",
    "--exclude-module", "PyQt5.QtWebEngineWidgets",
    "--exclude-module", "PyQt5.QtXmlPatterns",
    "--exclude-module", "tkinter",
    "--exclude-module", "unittest",
    "--exclude-module", "pydoc",

    # 数据文件
    "--add-data", f"config.example.json{os.pathsep}.",
    "--add-data", f"docs{os.pathsep}docs",
    "--add-data", f"ui/resources{os.pathsep}ui/resources",

    # 主脚本
    MAIN_SCRIPT,
]


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("错误: 未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        return False


def check_dependencies():
    """检查并显示依赖版本"""
    print(f"\n{APP_NAME} v{VERSION} 打包")
    print(f"平台: {platform.system()} {platform.machine()}")
    print("\n检查依赖库...")
    deps = [
        ("PyQt5", "PyQt5"),
        ("pyserial", "serial"),
        ("pyte", "pyte"),
        ("paramiko", "paramiko"),
    ]

    all_ok = True
    for name, module in deps:
        try:
            m = __import__(module)
            version = getattr(m, "__version__", getattr(m, "VERSION", "unknown"))
            print(f"  ✓ {name}: {version}")
        except ImportError:
            print(f"  ✗ {name}: 未安装")
            all_ok = False

    if not all_ok:
        print("\n请先安装缺失的依赖: pip install -r requirements.txt")

    return all_ok


def build():
    """执行打包"""
    if not check_pyinstaller():
        return False

    if not check_dependencies():
        return False

    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"\n工作目录: {script_dir}")

    # 添加图标（如果有）
    args = PYINSTALLER_ARGS.copy()
    if ICON_FILE and os.path.exists(ICON_FILE):
        args.insert(0, "--icon")
        args.insert(1, ICON_FILE)

    # 执行 PyInstaller
    print("\n开始打包（可能需要几分钟）...")
    print(f"命令: pyinstaller {' '.join(args[:10])}...\n")

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller"] + args,
        cwd=script_dir
    )

    if result.returncode != 0:
        print("\n打包失败!")
        return False

    # 复制额外文件到输出目录
    dist_dir = os.path.join(script_dir, "dist", APP_NAME)
    if os.path.exists(dist_dir):
        # 创建 logs 目录
        logs_dir = os.path.join(dist_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        # Copy the default template if it was not collected by PyInstaller.
        config_src = os.path.join(script_dir, "config.example.json")
        config_dst = os.path.join(dist_dir, "config.example.json")
        if os.path.exists(config_src) and not os.path.exists(config_dst):
            shutil.copy2(config_src, config_dst)

        print(f"\n" + "="*50)
        print(f"打包成功!")
        print(f"="*50)
        print(f"版本: v{VERSION}")
        print(f"输出目录: {dist_dir}")
        if sys.platform == "win32":
            exe_path = os.path.join(dist_dir, APP_NAME + '.exe')
            print(f"可执行文件: {exe_path}")
        else:
            exe_path = os.path.join(dist_dir, APP_NAME)
            print(f"可执行文件: {exe_path}")

        # 创建发布包
        create_release(dist_dir)

        print(f"\n提示: 分发时需要将整个 {APP_NAME} 目录一起打包")

    return True


def build_onefile():
    """打包成单个可执行文件（启动较慢但方便分发）"""
    global PYINSTALLER_ARGS
    # 替换 --onedir 为 --onefile
    args = [arg if arg != "--onedir" else "--onefile" for arg in PYINSTALLER_ARGS]
    PYINSTALLER_ARGS = args
    return build()


def create_release(dist_dir):
    """创建发布包"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    release_dir = os.path.join(script_dir, "release")
    os.makedirs(release_dir, exist_ok=True)

    # 确定平台名称
    if sys.platform == "win32":
        platform_name = "windows"
    elif sys.platform == "darwin":
        platform_name = "macos"
    else:
        platform_name = "linux"

    arch = platform.machine().lower()
    if arch in ("x86_64", "amd64"):
        arch = "amd64"
    elif arch in ("aarch64", "arm64"):
        arch = "arm64"

    release_name = f"{APP_NAME}_v{VERSION}_{platform_name}_{arch}"
    release_path = os.path.join(release_dir, release_name)

    # 复制到 release 目录
    if os.path.exists(release_path):
        shutil.rmtree(release_path)
    def ignore_release_files(src, names):
        ignored = set()
        rel = os.path.relpath(src, dist_dir)
        in_logs_dir = rel == "logs" or rel.endswith(os.sep + "logs")
        for name in names:
            path = os.path.join(src, name)
            if in_logs_dir or name == "logs":
                ignored.add(name)
            elif fnmatch.fnmatch(name.lower(), "*.log"):
                ignored.add(name)
        return ignored

    shutil.copytree(dist_dir, release_path, ignore=ignore_release_files)
    os.makedirs(os.path.join(release_path, "logs"), exist_ok=True)

    print(f"\n发布目录: {release_path}")

    # 创建压缩包
    if sys.platform == "win32":
        # Windows: 尝试用 7z 创建 zip
        zip_path = f"{release_path}.zip"
        try:
            subprocess.run(["7z", "a", "-tzip", zip_path, release_path],
                         check=True, capture_output=True)
            print(f"发布包: {zip_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("提示: 安装 7-Zip 可自动创建 zip 包")
    else:
        # Linux/macOS: 创建 tar.gz
        tar_path = f"{release_path}.tar.gz"
        import tarfile
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(release_path, arcname=release_name)
        print(f"发布包: {tar_path}")


def clean():
    """清理打包产生的临时文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    dirs_to_remove = ["build", "dist", "release", "__pycache__"]
    files_to_remove = [f"{APP_NAME}.spec"]

    for d in dirs_to_remove:
        path = os.path.join(script_dir, d)
        if os.path.exists(path):
            print(f"删除目录: {path}")
            shutil.rmtree(path)

    for f in files_to_remove:
        path = os.path.join(script_dir, f)
        if os.path.exists(path):
            print(f"删除文件: {path}")
            os.remove(path)

    # 清理子目录的 __pycache__
    for root, dirs, files in os.walk(script_dir):
        for d in dirs:
            if d == "__pycache__":
                path = os.path.join(root, d)
                print(f"删除目录: {path}")
                shutil.rmtree(path)

    print("清理完成")


def print_help():
    """打印帮助信息"""
    print(f"""
{APP_NAME} v{VERSION} 打包脚本

用法:
    python build.py          # 打包成目录（推荐，启动快）
    python build.py onefile  # 打包成单个exe（方便分发，启动慢）
    python build.py clean    # 清理临时文件
    python build.py help     # 显示帮助

注意:
    1. 打包前请确保已安装所有依赖: pip install -r requirements.txt
    2. 打包前请确保已安装 PyInstaller: pip install pyinstaller
    3. 打包后的程序在 dist/{APP_NAME} 目录下
    4. 发布包在 release/ 目录下
""")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "clean":
            clean()
        elif cmd == "onefile":
            build_onefile()
        elif cmd == "help" or cmd == "-h" or cmd == "--help":
            print_help()
        else:
            print(f"未知命令: {cmd}")
            print_help()
    else:
        build()

