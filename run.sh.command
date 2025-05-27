#!/bin/bash

# 将工作目录切换到脚本所在的目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || { echo "切换目录失败"; read -p "按回车键退出..."; exit 1; }
echo "已切换到脚本所在目录: $SCRIPT_DIR"

# 检测操作系统类型
OS_TYPE="unknown"
if [[ "$(uname)" == "Darwin" ]]; then
    OS_TYPE="macos"
elif [[ "$(uname)" == "Linux" ]]; then
    OS_TYPE="linux"
    # 检测常见的 Linux 发行版
    if [[ -f /etc/debian_version ]]; then
        DISTRO="debian"
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO="redhat"
    elif [[ -f /etc/arch-release ]]; then
        DISTRO="arch"
    else
        DISTRO="unknown"
    fi
fi

echo "检测到操作系统: $OS_TYPE"
if [[ "$OS_TYPE" == "linux" ]]; then
    echo "Linux 发行版: $DISTRO"
fi

# 检查是否安装了 Homebrew（macOS）
if [[ "$OS_TYPE" == "macos" ]]; then
    echo "检查是否安装了 Homebrew..."
    if ! command -v brew &>/dev/null; then
        echo "Homebrew 未安装，准备安装..."
        # 使用中国大陆可用的软件源
        echo "使用中国大陆镜像源安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/Homebrew.sh)"

        if ! command -v brew &>/dev/null; then
            echo "安装 Homebrew 失败，请手动安装: https://brew.sh/"
            read -p "按回车键退出..."
            exit 1
        fi
        echo "Homebrew 安装完成"
    else
        echo "检测到 Homebrew 已安装"
    fi
fi

# 检查是否安装了 ffmpeg
echo "检查是否安装了 ffmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg 未安装，准备安装..."

    if [[ "$OS_TYPE" == "macos" ]]; then
        echo "在 macOS 上安装 ffmpeg..."
        echo "使用 Homebrew 安装 ffmpeg..."
        brew install ffmpeg
        if [[ $? -ne 0 ]]; then
            echo "安装 ffmpeg 失败"
            read -p "按回车键退出..."
            exit 1
        fi

    elif [[ "$OS_TYPE" == "linux" ]]; then
        if [[ "$DISTRO" == "debian" ]]; then
            echo "在 Debian/Ubuntu 上安装 ffmpeg..."
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif [[ "$DISTRO" == "redhat" ]]; then
            echo "在 RHEL/CentOS/Fedora 上安装 ffmpeg..."
            sudo yum install -y epel-release
            sudo yum install -y ffmpeg ffmpeg-devel
        elif [[ "$DISTRO" == "arch" ]]; then
            echo "在 Arch Linux 上安装 ffmpeg..."
            sudo pacman -S ffmpeg
        else
            echo "不支持的 Linux 发行版，请手动安装 ffmpeg"
            read -p "按回车键退出..."
            exit 1
        fi

        if [[ $? -ne 0 ]]; then
            echo "安装 ffmpeg 失败"
            read -p "按回车键退出..."
            exit 1
        fi
    else
        echo "不支持的操作系统，请手动安装 ffmpeg"
        read -p "按回车键退出..."
        exit 1
    fi

    echo "ffmpeg 安装完成"
else
    echo "检测到 ffmpeg 已安装"
fi

# 初始化 Python 命令变量为空
PYTHON_CMD=""
PYTHON310_CMD=""

# 检查是否有 Python 3.10
if command -v python3.10 &>/dev/null; then
    PYTHON310_CMD="python3.10"
    PYTHON_CMD="python3.10"
    echo "找到 Python 3.10"
# 检查其他 Python 版本
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

# 如果找到了 Python，检查版本
if [[ -n "$PYTHON_CMD" ]]; then
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1)
    if [[ $? -ne 0 ]]; then
        echo "错误: 获取 Python 版本失败: $PYTHON_VERSION"
        read -p "按回车键退出..."
        exit 1
    fi

    # 检查版本是否满足要求
    if ! command -v bc &>/dev/null; then
        if [[ "$PYTHON_VERSION" < "3.10" ]]; then
            echo "检测到 Python 版本为 $PYTHON_VERSION，但需要 3.10 或更高版本"
            NEED_INSTALL=true
        fi
    else
        if ! (( $(echo "$PYTHON_VERSION == 3.10" | bc -l) )); then
            echo "检测到 Python 版本为 $PYTHON_VERSION，但需要 3.10 "
            NEED_INSTALL=true
        else
            NEED_INSTALL=false
        fi
    fi
else
    echo "未检测到 Python，需要安装 Python 3.10"
    NEED_INSTALL=true
fi

# 安装 Python 3.10（如果需要）
if [[ "$NEED_INSTALL" == "true" ]]; then
    echo "准备安装 Python 3.10..."

    if [[ "$OS_TYPE" == "macos" ]]; then
        echo "在 macOS 上安装 Python 3.10..."
        echo "使用 Homebrew 安装 Python 3.10..."
        # 设置 Homebrew 使用中国源
        echo "配置 Homebrew 使用中国源..."
        brew update
        brew tap --custom-remote --force-auto-update homebrew/core https://mirrors.ustc.edu.cn/homebrew-core.git
        brew tap --custom-remote --force-auto-update homebrew/cask https://mirrors.ustc.edu.cn/homebrew-cask.git

        # 安装 Python 3.10
        brew install python@3.10
        if [[ $? -ne 0 ]]; then
            echo "安装 Python 3.10 失败"
            read -p "按回车键退出..."
            exit 1
        fi

        PYTHON_CMD="python3.10"

    elif [[ "$OS_TYPE" == "linux" ]]; then
        if [[ "$DISTRO" == "debian" ]]; then
            echo "在 Debian/Ubuntu 上安装 Python 3.10..."
            sudo apt-get update
            sudo apt-get install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt-get update
            sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
        elif [[ "$DISTRO" == "redhat" ]]; then
            echo "在 RHEL/CentOS/Fedora 上安装 Python 3.10..."
            sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel
            cd /tmp
            wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz
            tar xzf Python-3.10.0.tgz
            cd Python-3.10.0
            ./configure --enable-optimizations
            sudo make altinstall
            cd "$SCRIPT_DIR"
        elif [[ "$DISTRO" == "arch" ]]; then
            echo "在 Arch Linux 上安装 Python 3.10..."
            sudo pacman -S python310
        else
            echo "不支持的 Linux 发行版，请手动安装 Python 3.10"
            read -p "按回车键退出..."
            exit 1
        fi

        if [[ $? -ne 0 ]]; then
            echo "安装 Python 3.10 失败"
            read -p "按回车键退出..."
            exit 1
        fi

        PYTHON_CMD="python3.10"
    else
        echo "不支持的操作系统，请手动安装 Python 3.10"
        read -p "按回车键退出..."
        exit 1
    fi

    echo "Python 3.10 安装完成"
fi

# 再次验证 Python 版本
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1)
if [[ $? -ne 0 ]]; then
    echo "错误: 获取 Python 版本失败: $PYTHON_VERSION"
    read -p "按回车键退出..."
    exit 1
fi

echo "使用 Python 版本: $PYTHON_VERSION"

# 如果版本检查通过，继续执行后续操作
echo "开始执行主程序..."

# 创建虚拟环境
echo "正在创建虚拟环境..."
$PYTHON_CMD -m venv venv
if [[ $? -ne 0 ]]; then
    echo "错误: 创建虚拟环境失败"
    read -p "按回车键退出..."
    exit 1
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source venv/bin/activate
if [[ $? -ne 0 ]]; then
    echo "错误: 激活虚拟环境失败"
    read -p "按回车键退出..."
    exit 1
fi

# 配置pip使用中国大陆镜像源
echo "配置pip使用中国大陆镜像源..."
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装依赖
echo "正在安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt
if [[ $? -ne 0 ]]; then
    echo "错误: 安装依赖失败"
    read -p "按回车键退出..."
    exit 1
fi

# 运行应用程序
echo "正在启动应用程序..."
which python
venv/bin/python app.py
app_exit_code=$?

if [[ $app_exit_code -ne 0 ]]; then
    echo "应用程序已退出，退出码: $app_exit_code"
    read -p "按回车键退出..."
fi